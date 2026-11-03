"""Avisos dentro de Momento.

Cada aviso pertenece a una cuenta y solo lo ve esa cuenta. La web los consulta cada
minuto; las familias usan las mismas rutas bajo /api/family. La app móvil (Fase 7)
usará estas rutas y podrá sumar avisos push.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from momento_api.auth import get_authenticated_account
from momento_api.models import (
    FamilyAuthorization,
    FamilyUpdate,
    Notification,
    OrganizationMembership,
    SharedCareCategory,
    UserAccount,
    UserGroup,
)
from momento_api.session import get_session

# Sin prefijo propio: main.py lo monta en /api (personal) y en /api/family (familias).
router = APIRouter(prefix="/notifications", tags=["Avisos"])


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
    """Solo avisos que la cuenta sigue teniendo derecho a ver.

    Personal: avisos de servicios a los que llega como personal activo. Si la pasan a
    otro servicio o la desactivan, deja de ver los anteriores (nombran a residentes).
    Familias: avisos de novedades vigentes de personas que sigue teniendo autorizadas
    para "Novedades"; si se revoca el permiso o se retira la novedad, el aviso desaparece.
    """
    reachable = (
        select(OrganizationMembership.organization_id, OrganizationMembership.care_unit_id)
        .where(
            OrganizationMembership.user_account_id == account.id,
            OrganizationMembership.is_active.is_(True),
            OrganizationMembership.user_group == UserGroup.STAFF,
        )
        .subquery()
    )
    staff = and_(
        Notification.kind != "family_update",
        select(1).where(
            reachable.c.organization_id == Notification.organization_id,
            or_(
                reachable.c.care_unit_id.is_(None),
                Notification.care_unit_id.is_(None),
                reachable.c.care_unit_id == Notification.care_unit_id,
            ),
        ).exists(),
    )
    family = and_(
        Notification.kind == "family_update",
        select(1)
        .select_from(FamilyUpdate)
        .join(FamilyAuthorization, FamilyAuthorization.care_recipient_id == FamilyUpdate.care_recipient_id)
        .join(OrganizationMembership, OrganizationMembership.id == FamilyAuthorization.family_membership_id)
        .where(
            FamilyUpdate.id == Notification.target_id,
            FamilyUpdate.withdrawn_at.is_(None),
            FamilyAuthorization.category == SharedCareCategory.UPDATES,
            FamilyAuthorization.is_active.is_(True),
            FamilyAuthorization.can_view.is_(True),
            OrganizationMembership.user_account_id == account.id,
            OrganizationMembership.user_group == UserGroup.FAMILY,
            OrganizationMembership.is_active.is_(True),
        )
        .exists(),
    )
    return (Notification.user_account_id == account.id, or_(staff, family))


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
