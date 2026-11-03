"""Novedades para la familia (Fase 5, primera entrega).

Nada del registro diario llega solo a la familia. Una persona del equipo, con un puesto
habilitado en la configuración del servicio, escribe la novedad o parte de un registro
del día y revisa el texto antes de publicarlo. La ven solo las cuentas familiares con el
permiso "Novedades" activo para esa persona. No se edita: si hay un error, quien la
publicó (o el encargado) la retira con un motivo y la familia deja de verla.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from momento_api.audit import record_event
from momento_api.auth import get_authenticated_account
from momento_api.care_log import _active_recipient, _is_manager, _unit_and_member, _utc
from momento_api.care_settings import settings_for
from momento_api.family_requests import get_family_memberships
from momento_api.models import (
    CareEntry,
    CareRecipient,
    CareUnit,
    FamilyAuthorization,
    FamilyUpdate,
    OrganizationMembership,
    SharedCareCategory,
    UserAccount,
)
from momento_api.notifications import notify
from momento_api.session import get_session

router = APIRouter(prefix="/api/care-units", tags=["Novedades para la familia"])
family_router = APIRouter(prefix="/api/family", tags=["Acceso familiar"])

ROLE_LABELS = {"manager": "Encargado/a", "administrative": "Administración", "physician": "Médico/a", "caregiver": "Cuidador/a"}


class UpdateCreate(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    source_entry_id: UUID | None = None

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Escribí la novedad.")
        return value


class WithdrawInput(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


_LOAD = (
    selectinload(FamilyUpdate.recipient),
    selectinload(FamilyUpdate.published_by).selectinload(OrganizationMembership.user),
    selectinload(FamilyUpdate.withdrawn_by).selectinload(OrganizationMembership.user),
)


def _readers(session: Session, recipient_id: UUID) -> list[OrganizationMembership]:
    """Cuentas familiares activas con permiso para ver novedades de esta persona."""
    return list(session.scalars(
        select(OrganizationMembership)
        .options(selectinload(OrganizationMembership.user))
        .join(FamilyAuthorization, FamilyAuthorization.family_membership_id == OrganizationMembership.id)
        .where(
            FamilyAuthorization.care_recipient_id == recipient_id,
            FamilyAuthorization.category == SharedCareCategory.UPDATES,
            FamilyAuthorization.is_active.is_(True),
            FamilyAuthorization.can_view.is_(True),
            OrganizationMembership.is_active.is_(True),
        )
    ).all())


def _can_publish(member: OrganizationMembership, settings: dict) -> bool:
    return member.staff_role is not None and member.staff_role.value in settings["family_update_roles"]


def _staff_read(update: FamilyUpdate, account: UserAccount, manager: bool) -> dict[str, object]:
    return {
        "id": str(update.id),
        "text": update.text,
        "published_at": _utc(update.published_at).isoformat(),
        "published_by_name": update.published_by.user.display_name,
        "from_entry": update.source_entry_id is not None,
        "withdrawn": update.withdrawn_at is not None,
        "withdraw_reason": update.withdraw_reason,
        "withdrawn_by_name": update.withdrawn_by.user.display_name if update.withdrawn_by else None,
        "can_withdraw": update.withdrawn_at is None and (manager or update.published_by.user_account_id == account.id),
    }


@router.get("/{care_unit_id}/care-recipients/{recipient_id}/family-updates")
def list_updates(
    care_unit_id: UUID,
    recipient_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, object]:
    """Lo publicado para la familia, quién lo ve y si quien consulta puede publicar."""
    care_unit, member = _unit_and_member(session, account, care_unit_id)
    recipient = _active_recipient(session, care_unit, recipient_id)
    updates = session.scalars(
        select(FamilyUpdate).options(*_LOAD)
        .where(FamilyUpdate.care_recipient_id == recipient.id)
        .order_by(FamilyUpdate.published_at.desc()).limit(50)
    ).all()
    manager = _is_manager(session, account, care_unit)
    return {
        "updates": [_staff_read(item, account, manager) for item in updates],
        "readers": sorted(m.user.display_name for m in _readers(session, recipient.id) if m.user.is_active),
        "can_publish": _can_publish(member, settings_for(care_unit)),
    }


@router.post("/{care_unit_id}/care-recipients/{recipient_id}/family-updates", status_code=status.HTTP_201_CREATED)
def publish_update(
    care_unit_id: UUID,
    recipient_id: UUID,
    payload: UpdateCreate,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, object]:
    care_unit, member = _unit_and_member(session, account, care_unit_id)
    recipient = _active_recipient(session, care_unit, recipient_id)
    settings = settings_for(care_unit)
    if not _can_publish(member, settings):
        raise HTTPException(status_code=403, detail="Tu puesto no publica novedades para la familia en este servicio.")
    if payload.source_entry_id is not None:
        entry = session.get(CareEntry, payload.source_entry_id)
        if entry is None or entry.care_recipient_id != recipient.id or entry.voided_at is not None:
            raise HTTPException(status_code=404, detail="Registro no encontrado.")
    readers = [m for m in _readers(session, recipient.id) if m.user.is_active]
    if not readers:
        raise HTTPException(
            status_code=409,
            detail="Ningún familiar tiene permiso para ver novedades de esta persona. Habilitalo en Usuarios y vínculos.",
        )
    update = FamilyUpdate(
        care_unit_id=care_unit.id, care_recipient_id=recipient.id, text=payload.text,
        source_entry_id=payload.source_entry_id, published_by_membership_id=member.id,
    )
    session.add(update)
    session.flush()
    record_event(
        session, action="family_update.published", actor_account_id=account.id,
        organization_id=care_unit.organization_id, target_type="care_recipient", target_id=recipient.id,
        details={"update_id": str(update.id), "readers": len(readers)},
    )
    if settings["family_update_notify"]:
        notify(
            session, account_ids=[m.user_account_id for m in readers], organization_id=care_unit.organization_id,
            care_unit_id=care_unit.id, kind="family_update",
            title=f"Novedad sobre {recipient.preferred_name or recipient.display_name}",
            target_type="family_update", target_id=update.id,
        )
    session.commit()
    created = session.scalar(select(FamilyUpdate).options(*_LOAD).where(FamilyUpdate.id == update.id))
    return _staff_read(created, account, _is_manager(session, account, care_unit))


@router.post("/{care_unit_id}/family-updates/{update_id}/withdraw")
def withdraw_update(
    care_unit_id: UUID,
    update_id: UUID,
    payload: WithdrawInput,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, object]:
    care_unit, member = _unit_and_member(session, account, care_unit_id)
    update = session.scalar(
        select(FamilyUpdate).options(*_LOAD).where(FamilyUpdate.id == update_id, FamilyUpdate.care_unit_id == care_unit.id)
    )
    if update is None:
        raise HTTPException(status_code=404, detail="Novedad no encontrada.")
    manager = _is_manager(session, account, care_unit)
    if not (manager or update.published_by.user_account_id == account.id):
        raise HTTPException(status_code=403, detail="Solo quien la publicó o el encargado puede retirarla.")
    if update.withdrawn_at is not None:
        raise HTTPException(status_code=409, detail="La novedad ya fue retirada.")
    update.withdrawn_at = datetime.now(timezone.utc)
    update.withdrawn_by_membership_id = member.id
    update.withdraw_reason = payload.reason.strip()
    record_event(
        session, action="family_update.withdrawn", actor_account_id=account.id,
        organization_id=care_unit.organization_id, target_type="care_recipient", target_id=update.care_recipient_id,
        details={"update_id": str(update.id)},
    )
    session.commit()
    session.refresh(update)
    return _staff_read(update, account, manager)


@family_router.get("/updates")
def family_updates(
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
    memberships: list[OrganizationMembership] = Depends(get_family_memberships),
) -> list[dict[str, object]]:
    """Novedades vigentes de las personas que esta cuenta tiene autorizadas para "Novedades"."""
    allowed = select(FamilyAuthorization.care_recipient_id).where(
        FamilyAuthorization.family_membership_id.in_([m.id for m in memberships]),
        FamilyAuthorization.category == SharedCareCategory.UPDATES,
        FamilyAuthorization.is_active.is_(True),
        FamilyAuthorization.can_view.is_(True),
    )
    rows = session.execute(
        select(FamilyUpdate, CareUnit)
        .options(selectinload(FamilyUpdate.recipient), selectinload(FamilyUpdate.published_by))
        .join(CareRecipient, CareRecipient.id == FamilyUpdate.care_recipient_id)
        .join(CareUnit, CareUnit.id == FamilyUpdate.care_unit_id)
        .where(
            FamilyUpdate.care_recipient_id.in_(allowed),
            FamilyUpdate.withdrawn_at.is_(None),
            CareRecipient.is_active.is_(True),
        )
        .order_by(FamilyUpdate.published_at.desc()).limit(100)
    ).all()
    for organization_id in {unit.organization_id for _, unit in rows}:
        record_event(session, action="family_updates.viewed", actor_account_id=account.id, organization_id=organization_id)
    session.commit()
    return [
        {
            "id": str(update.id),
            "care_recipient_id": str(update.care_recipient_id),
            "care_recipient_name": update.recipient.preferred_name or update.recipient.display_name,
            "care_unit_name": unit.name,
            "text": update.text,
            # A la familia se le muestra el puesto, no el nombre de quien publicó.
            "published_by_role": ROLE_LABELS.get(update.published_by.staff_role.value, "Equipo")
            if update.published_by.staff_role else "Equipo",
            "published_at": _utc(update.published_at).isoformat(),
        }
        for update, unit in rows
    ]
