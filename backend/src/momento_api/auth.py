"""Autenticación local con contraseñas derivadas y sesiones revocables."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from momento_api.models import AuthSession, Organization, OrganizationMembership, UserAccount, UserCredential, UserGroup
from momento_api.session import get_session

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])
COOKIE_NAME = "momento_session"
SESSION_HOURS = 8
PASSWORD_MIN_LENGTH = 12
_attempts: dict[str, deque[float]] = defaultdict(deque)
_DUMMY_HASH = "$".join(("scrypt", "16384", "8", "1", "bW9tZW50by1kZW1teS1zYWx0IQ==", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="))


class LoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("Ingresá un correo válido.")
        return value


def hash_password(password: str) -> str:
    """Deriva una clave con scrypt y sal aleatoria para almacenarla."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres.")
    salt = secrets.token_bytes(16)
    params = {"n": 2**14, "r": 8, "p": 1}
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, **params, dklen=64)
    return "$".join((
        "scrypt", str(params["n"]), str(params["r"]), str(params["p"]),
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode(),
    ))


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt64, digest64 = encoded.split("$")
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt64.encode())
        expected = base64.urlsafe_b64decode(digest64.encode())
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=salt,
            n=int(n), r=int(r), p=int(p), dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, MemoryError):
        return False


def _ip_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _enforce_login_limit(request: Request) -> None:
    now = time.monotonic()
    attempts = _attempts[_ip_key(request)]
    while attempts and now - attempts[0] > 900:
        attempts.popleft()
    if len(attempts) >= 10:
        raise HTTPException(status_code=429, detail="Demasiados intentos. Esperá unos minutos y volvé a intentar.")
    attempts.append(now)


def _auth_error() -> HTTPException:
    return HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")


def _session_payload(account: UserAccount, session: Session) -> dict[str, object]:
    memberships = session.scalars(
        select(OrganizationMembership)
        .join(Organization, Organization.id == OrganizationMembership.organization_id)
        .where(
            OrganizationMembership.user_account_id == account.id,
            OrganizationMembership.is_active.is_(True),
            Organization.is_active.is_(True),
        )
        .order_by(Organization.name, OrganizationMembership.id)
    ).all()
    return {
        "user": {"id": str(account.id), "display_name": account.display_name, "email": account.email},
        "memberships": [
            {
                "id": str(item.id),
                "organization_id": str(item.organization_id),
                "organization_name": item.organization.name,
                "care_unit_id": str(item.care_unit_id) if item.care_unit_id else None,
                "user_group": item.user_group.value,
                "role_label": item.role_label,
            }
            for item in memberships
        ],
    }


def _cookie_secure() -> bool:
    return os.getenv("MOMENTO_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes"}


@router.post("/login")
def login(
    payload: LoginInput,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    _enforce_login_limit(request)
    accounts = session.scalars(
        select(UserAccount).where(func.lower(UserAccount.email) == payload.email, UserAccount.is_active.is_(True)).limit(2)
    ).all()
    account = accounts[0] if len(accounts) == 1 else None
    credential = session.get(UserCredential, account.id) if account else None
    membership_id = session.scalar(
        select(OrganizationMembership.id).where(
            OrganizationMembership.user_account_id == account.id,
            OrganizationMembership.is_active.is_(True),
        ).limit(1)
    ) if account else None
    password_ok = verify_password(
        payload.password,
        credential.password_hash if credential is not None else _DUMMY_HASH,
    )
    if account is None or credential is None or membership_id is None or not password_ok:
        raise _auth_error()



def get_management_account(
    account: UserAccount = Depends(get_authenticated_account),
    session: Session = Depends(get_session),
) -> UserAccount:
    """Limita el área administrativa a cuentas con un vínculo activo de personal."""
    staff_membership = session.scalar(
        select(OrganizationMembership.id).where(
            OrganizationMembership.user_account_id == account.id,
            OrganizationMembership.is_active.is_(True),
            OrganizationMembership.user_group == UserGroup.STAFF,
        ).limit(1)
    )
    if staff_membership is None:
        raise HTTPException(status_code=403, detail="Tu cuenta no tiene acceso al área de gestión.")
    return account
