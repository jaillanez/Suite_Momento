"""Invitaciones y recuperación de contraseña por correo.

- Recuperar: la persona pide un enlace desde la pantalla de ingreso. Solo se envía si la
  cuenta ya tiene contraseña; las cuentas nuevas se activan con la invitación del encargado.
- Invitar: el encargado envía un enlace para que la persona cree su contraseña.

La respuesta al pedido de recuperación es siempre la misma, exista o no la cuenta.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from momento_api.auth import _record_for_each_organization, hash_password
from momento_api.mailer import mail_settings, send_mail
from momento_api.models import (
    AuthSession,
    OrganizationMembership,
    PasswordToken,
    UserAccount,
    UserCredential,
)
from momento_api.session import get_session

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

# Vigencia de los enlaces. Ajustar acá si el equipo define otros plazos.
LINK_HOURS = {"reset": 1, "invite": 72}
_requests: dict[str, deque[float]] = defaultdict(deque)
GENERIC_REPLY = {"detail": "Si el correo corresponde a una cuenta con acceso, te enviamos un enlace."}


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def cancel_pending_links(session: Session, account_id: UUID) -> None:
    """Anula los enlaces sin usar: al crear uno nuevo, cambiar la contraseña o desactivar el acceso."""
    now = datetime.now(timezone.utc)
    for pending in session.scalars(
        select(PasswordToken).where(
            PasswordToken.user_account_id == account_id,
            PasswordToken.used_at.is_(None),
        )
    ).all():
        pending.used_at = now


def issue_link(session: Session, account: UserAccount, purpose: str) -> str:
    """Crea un enlace nuevo y anula los anteriores sin usar de la misma cuenta."""
    now = datetime.now(timezone.utc)
    cancel_pending_links(session, account.id)
    token = secrets.token_urlsafe(32)
    session.add(PasswordToken(
        user_account_id=account.id,
        token_hash=_hash(token),
        purpose=purpose,
        expires_at=now + timedelta(hours=LINK_HOURS[purpose]),
    ))
    return token


def queue_link_email(
    background: BackgroundTasks,
    account: UserAccount,
    token: str,
    purpose: str,
    organization_name: str | None = None,
) -> None:
    """El envío ocurre después de responder, para no demorar ni revelar nada por tiempo."""
    url = f"{mail_settings().public_url}/#restablecer={token}"
    hours = LINK_HOURS[purpose]
    if purpose == "invite":
        subject = "Tu acceso a Momento"
        intro = f"{organization_name or 'Tu organización'} te dio acceso a Momento."
        action = "Para crear tu contraseña, entrá a este enlace"
    else:
        subject = "Recuperar tu contraseña de Momento"
        intro = "Recibimos un pedido para cambiar tu contraseña."
        action = "Para elegir una nueva, entrá a este enlace"
    body = (
        f"Hola {account.display_name}:\n\n{intro}\n\n{action}:\n{url}\n\n"
        f"El enlace sirve una sola vez y vence en {hours} hora{'s' if hours != 1 else ''}.\n"
        "Si no lo pediste, ignorá este correo; tu cuenta no cambia.\n\nMomento"
    )
    background.add_task(send_mail, account.email or "", subject, body)


def _enforce_request_limit(request: Request) -> None:
    now = time.monotonic()
    attempts = _requests[request.client.host if request.client else "unknown"]
    while attempts and now - attempts[0] > 900:
        attempts.popleft()
    if len(attempts) >= 5:
        raise HTTPException(status_code=429, detail="Demasiados pedidos. Esperá unos minutos y volvé a intentar.")
    attempts.append(now)


class ResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class ResetConfirm(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=8, max_length=128)


@router.post("/password-reset/request", status_code=202)
def request_reset(
    payload: ResetRequest,
    request: Request,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    _enforce_request_limit(request)
    email = payload.email.strip().lower()
    accounts = session.scalars(
        select(UserAccount).where(func.lower(UserAccount.email) == email, UserAccount.is_active.is_(True)).limit(2)
    ).all()
    account = accounts[0] if len(accounts) == 1 else None
    if account is None or session.get(UserCredential, account.id) is None or session.scalar(
        select(OrganizationMembership.id).where(
            OrganizationMembership.user_account_id == account.id,
            OrganizationMembership.is_active.is_(True),
        ).limit(1)
    ) is None:
        return GENERIC_REPLY
    token = issue_link(session, account, "reset")
    _record_for_each_organization(session, action="auth.password_reset_requested", account_id=account.id)
    session.commit()
    queue_link_email(background, account, token, "reset")
    return GENERIC_REPLY


@router.post("/password-reset/confirm", status_code=204)
def confirm_reset(payload: ResetConfirm, session: Session = Depends(get_session)) -> Response:
    now = datetime.now(timezone.utc)
    link = session.scalar(select(PasswordToken).where(PasswordToken.token_hash == _hash(payload.token)))
    expires_at = link.expires_at if link is not None else None
    if expires_at is not None and expires_at.tzinfo is None:  # SQLite devuelve fechas sin zona
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    account = session.get(UserAccount, link.user_account_id) if link is not None else None
    has_access = account is not None and session.scalar(
        select(OrganizationMembership.id).where(
            OrganizationMembership.user_account_id == account.id,
            OrganizationMembership.is_active.is_(True),
        ).limit(1)
    ) is not None
    if link is None or link.used_at is not None or expires_at is None or expires_at <= now \
            or account is None or not account.is_active or not has_access:
        raise HTTPException(status_code=400, detail="El enlace venció o ya se usó. Pedí uno nuevo.")

    try:
        password_hash = hash_password(payload.password)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    credential = session.get(UserCredential, account.id)
    if credential is None:
        session.add(UserCredential(user_account_id=account.id, password_hash=password_hash))
    else:
        credential.password_hash = password_hash
    link.used_at = now
    for auth_session in session.scalars(
        select(AuthSession).where(AuthSession.user_account_id == account.id, AuthSession.revoked_at.is_(None))
    ).all():
        auth_session.revoked_at = now
    _record_for_each_organization(session, action=f"account.password_set_by_{link.purpose}", account_id=account.id)
    session.commit()
    return Response(status_code=204)
