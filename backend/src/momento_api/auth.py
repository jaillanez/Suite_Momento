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
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from momento_api.audit import record_event
from momento_api.models import (
    AuthSession,
    CareUnit,
    Organization,
    OrganizationMembership,
    StaffRole,
    UserAccount,
    UserCredential,
    UserGroup,
)
from momento_api.session import get_session

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])
COOKIE_NAME = "momento_session"
SESSION_HOURS = 8
PASSWORD_MIN_LENGTH = 8
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}
_attempts: dict[str, deque[float]] = defaultdict(deque)


class LoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("Ingresá un correo válido.")
        return normalized


def hash_password(password: str) -> str:
    """Deriva una clave con scrypt y sal aleatoria para almacenarla."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres.")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT, dklen=64)
    return "$".join((
        "scrypt",
        str(_SCRYPT["n"]),
        str(_SCRYPT["r"]),
        str(_SCRYPT["p"]),
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    ))


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt64, digest64 = encoded.split("$")
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest64.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, MemoryError):
        return False


_DUMMY_HASH = hash_password("momento-unknown-account-sentinel")


def _ip_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _enforce_login_limit(request: Request) -> None:
    now = time.monotonic()
    attempts = _attempts[_ip_key(request)]
    while attempts and now - attempts[0] > 900:
        attempts.popleft()
    if len(attempts) >= 10:
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos. Esperá unos minutos y volvé a intentar.",
        )
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
        "user": {
            "id": str(account.id),
            "display_name": account.display_name,
            "email": account.email,
        },
        "memberships": [
            {
                "id": str(membership.id),
                "organization_id": str(membership.organization_id),
                "organization_name": membership.organization.name,
                "care_unit_id": (
                    str(membership.care_unit_id) if membership.care_unit_id else None
                ),
                "user_group": membership.user_group.value,
                "role_label": membership.role_label,
                "staff_role": (
                    membership.staff_role.value if membership.staff_role else None
                ),
                "handles_inbox": membership.handles_inbox,
            }
            for membership in memberships
        ],
    }


def _cookie_secure() -> bool:
    return os.getenv("MOMENTO_COOKIE_SECURE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _record_for_each_organization(
    session: Session,
    *,
    action: str,
    account_id: UUID | None,
    outcome: str = "success",
) -> None:
    """Registra el evento una vez por organización de la cuenta.

    Así cada encargado ve solo los eventos de su organización. Sin cuenta
    conocida, el evento queda sin organización y no aparece en ningún listado.
    """
    organization_ids = (
        session.scalars(
            select(OrganizationMembership.organization_id)
            .where(OrganizationMembership.user_account_id == account_id)
            .distinct()
        ).all()
        if account_id is not None
        else []
    )
    for organization_id in organization_ids or [None]:
        record_event(
            session,
            action=action,
            actor_account_id=account_id,
            organization_id=organization_id,
            outcome=outcome,
        )


def _portal_membership_filter(portal: UserGroup):
    """Condición de acceso de cada portal; gestión y familia están separados."""
    conditions = [
        OrganizationMembership.is_active.is_(True),
        OrganizationMembership.user_group == portal,
    ]
    return conditions


def _login(
    payload: LoginInput,
    request: Request,
    response: Response,
    session: Session,
    portal: UserGroup,
) -> dict[str, object]:
    _enforce_login_limit(request)
    accounts = session.scalars(
        select(UserAccount)
        .where(
            func.lower(UserAccount.email) == payload.email,
            UserAccount.is_active.is_(True),
        )
        .limit(2)
    ).all()
    account = accounts[0] if len(accounts) == 1 else None
    credential = session.get(UserCredential, account.id) if account is not None else None
    has_portal_membership = (
        session.scalar(
            select(OrganizationMembership.id)
            .where(
                OrganizationMembership.user_account_id == account.id,
                *_portal_membership_filter(portal),
            )
            .limit(1)
        )
        if account is not None
        else None
    )
    password_valid = verify_password(
        payload.password,
        credential.password_hash if credential is not None else _DUMMY_HASH,
    )
    action = "auth.login" if portal is UserGroup.STAFF else "auth.family_login"
    if (
        account is None
        or credential is None
        or has_portal_membership is None
        or not password_valid
    ):
        # No se registra el correo ingresado para no guardar datos de terceros.
        _record_for_each_organization(
            session,
            action=action,
            account_id=account.id if account is not None else None,
            outcome="denied",
        )
        session.commit()
        raise _auth_error()

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    session.add(
        AuthSession(
            user_account_id=account.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS),
        )
    )
    _record_for_each_organization(session, action=action, account_id=account.id)
    session.commit()
    _attempts.pop(_ip_key(request), None)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_HOURS * 3600,
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        path="/api",
    )
    return _session_payload(account, session)


@router.post("/login")
def login(
    payload: LoginInput,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    """Acceso al panel de gestión: solo personal."""
    return _login(payload, request, response, session, UserGroup.STAFF)


@router.post("/family-login")
def family_login(
    payload: LoginInput,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    """Acceso familiar separado: solo cuentas con vínculo familiar activo."""
    return _login(payload, request, response, session, UserGroup.FAMILY)


def get_authenticated_account(
    request: Request,
    session: Session = Depends(get_session),
) -> UserAccount:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Iniciá sesión para continuar.")
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    account = session.scalar(
        select(UserAccount)
        .join(AuthSession, AuthSession.user_account_id == UserAccount.id)
        .where(
            AuthSession.token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(timezone.utc),
            UserAccount.is_active.is_(True),
        )
    )
    if account is None:
        raise HTTPException(
            status_code=401,
            detail="La sesión venció. Iniciá sesión nuevamente.",
        )
    return account


@router.get("/session")
def read_session(
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    """Informa si hay una sesión activa sin tratar la visita pública como error."""
    try:
        account = get_authenticated_account(request, session)
    except HTTPException as error:
        if error.status_code != 401:
            raise
        return {"authenticated": False, "user": None, "memberships": []}
    return {"authenticated": True, **_session_payload(account, session)}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> Response:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        auth_session = session.scalar(
            select(AuthSession).where(AuthSession.token_hash == token_hash)
        )
        if auth_session is not None and auth_session.revoked_at is None:
            auth_session.revoked_at = datetime.now(timezone.utc)
            _record_for_each_organization(
                session,
                action="auth.logout",
                account_id=auth_session.user_account_id,
            )
            session.commit()
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/api",
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


def get_management_account(
    request: Request,
    account: UserAccount = Depends(get_authenticated_account),
    session: Session = Depends(get_session),
) -> UserAccount:
    """Valida personal activo y limita cada ruta a su organización y servicio."""
    statement = select(OrganizationMembership.id).where(
        OrganizationMembership.user_account_id == account.id,
        OrganizationMembership.is_active.is_(True),
        OrganizationMembership.user_group == UserGroup.STAFF,
    )

    organization_id = request.path_params.get("organization_id")
    if organization_id:
        try:
            organization_uuid = UUID(organization_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Recurso no encontrado.") from None
        statement = statement.where(
            OrganizationMembership.organization_id == organization_uuid
        )

    care_unit_id = request.path_params.get("care_unit_id")
    if care_unit_id:
        try:
            unit_uuid = UUID(care_unit_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Recurso no encontrado.") from None
        unit_organization_id = (
            select(CareUnit.organization_id)
            .where(CareUnit.id == unit_uuid)
            .scalar_subquery()
        )
        statement = statement.where(
            OrganizationMembership.organization_id == unit_organization_id,
            or_(
                OrganizationMembership.care_unit_id.is_(None),
                OrganizationMembership.care_unit_id == unit_uuid,
            ),
        )

    if session.scalar(statement.limit(1)) is None:
        raise HTTPException(status_code=404, detail="Recurso no encontrado.")
    return account



def get_organization_admin_account(
    request: Request,
    account: UserAccount = Depends(get_authenticated_account),
    session: Session = Depends(get_session),
) -> UserAccount:
    """Permite acciones de configuración solo al encargado con alcance de organización."""
    statement = select(OrganizationMembership.id).where(
        OrganizationMembership.user_account_id == account.id,
        OrganizationMembership.is_active.is_(True),
        OrganizationMembership.user_group == UserGroup.STAFF,
        OrganizationMembership.staff_role == StaffRole.MANAGER,
        OrganizationMembership.care_unit_id.is_(None),
    )
    organization_id = request.path_params.get("organization_id")
    if organization_id:
        try:
            statement = statement.where(
                OrganizationMembership.organization_id == UUID(organization_id)
            )
        except ValueError:
            raise HTTPException(status_code=404, detail="Recurso no encontrado.") from None
    if session.scalar(statement.limit(1)) is None:
        raise HTTPException(status_code=403, detail="La acción requiere el puesto de encargado de la organización.")
    return account
