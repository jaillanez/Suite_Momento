"""Avisos dentro de Momento.

Cada aviso pertenece a una cuenta y solo lo ve esa cuenta. La web los consulta cada
minuto; la app móvil (Fase 7) usará estas mismas rutas y podrá sumar avisos push.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from momento_api.auth import get_authenticated_account
from momento_api.models import Notification, OrganizationMembership, UserAccount
from momento_api.session import get_session

router = APIRouter(prefix="/api/notifications", tags=["Avisos"])


def notify(
    session: Session,
    *,
    account_ids: list[UUID],
    organization_id: UUID,
    care_unit_id: UUID | None,
    kind: str,
    title: str,
    body: str | None = None,
    target_type: str | None = None,
    target_id: UUID | None = None,
) -> None:
    for account_id in dict.fromkeys(account_ids):
        session.add(Notification(
            user_account_id=account_id, organization_id=organization_id, care_unit_id=care_unit_id,
            kind=kind, title=title, body=body, target_type=target_type, target_id=target_id,
        ))


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _visible(account: UserAccount):
    """Solo avisos de organizaciones donde la cuenta sigue activa."""
    active_orgs = select(OrganizationMembership.organization_id).where(
        OrganizationMembership.user_account_id == account.id,
        OrganizationMembership.is_active.is_(True),
    )
    return (Notification.user_account_id == account.id, Notification.organization_id.in_(active_orgs))


@router.get("")
def list_notifications(
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, object]:
    items = session.scalars(
        select(Notification).where(*_visible(account)).order_by(Notification.created_at.desc()).limit(50)
    ).all()
    unread = session.scalar(
        select(func.count(Notification.id)).where(*_visible(account), Notification.read_at.is_(None))
    )
    return {
        "unread": unread or 0,
        "items": [
            {
                "id": str(item.id), "kind": item.kind, "title": item.title, "body": item.body,
                "care_unit_id": str(item.care_unit_id) if item.care_unit_id else None,
                "target_type": item.target_type, "target_id": str(item.target_id) if item.target_id else None,
                "created_at": _utc(item.created_at).isoformat(), "read": item.read_at is not None,
            }
            for item in items
        ],
    }


@router.post("/{notification_id}/read", status_code=204)
def mark_read(
    notification_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> Response:
    item = session.scalar(select(Notification).where(Notification.id == notification_id, *_visible(account)))
    if item is None:
        raise HTTPException(status_code=404, detail="Aviso no encontrado.")
    item.read_at = item.read_at or datetime.now(timezone.utc)
    session.commit()
    return Response(status_code=204)


@router.post("/read-all", status_code=204)
def mark_all_read(
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> Response:
    now = datetime.now(timezone.utc)
    for item in session.scalars(select(Notification).where(*_visible(account), Notification.read_at.is_(None))).all():
        item.read_at = now
    session.commit()
    return Response(status_code=204)
