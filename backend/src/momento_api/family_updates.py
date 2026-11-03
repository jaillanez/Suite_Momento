"""Novedades para la familia (Fase 5, primera entrega).

Nada del registro diario llega solo a la familia. Una persona del equipo, con un puesto
habilitado en la configuración del servicio, escribe la novedad o parte de un registro
del día y revisa el texto antes de publicarlo. La ven solo las cuentas familiares con el
permiso "Novedades" activo para esa persona. No se edita: si hay un error, quien la
publicó (o el encargado) la retira con un motivo y la familia deja de verla.

Fotos: solo si el servicio las permite y la persona tiene registrado su consentimiento
de imagen (quién lo dio y cuándo). Quien publica confirma además que no aparecen otras
personas o que también consintieron. Si se quita el consentimiento o el servicio deja de
permitir fotos, la familia deja de ver las fotos ya publicadas; el texto sigue visible.
"""

from __future__ import annotations

import base64
import binascii
import os
from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from momento_api.audit import record_event
from momento_api.auth import get_authenticated_account
from momento_api.care_log import _active_recipient, _is_manager, _unit_and_member, _utc
from momento_api.care_recipients import _roles
from momento_api.care_settings import settings_for
from momento_api.documents import storage_dir
from momento_api.family_requests import get_family_memberships
from momento_api.models import (
    FAMILY_AUTHORIZER_ROLES,
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


MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_SIGNATURES = {"image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG\r\n\x1a\n"}


class PhotoInput(BaseModel):
    content_type: Literal["image/jpeg", "image/png"]
    # Contenido en base64: evita sumar una dependencia para formularios multipart.
    data: str = Field(min_length=1, max_length=(MAX_PHOTO_BYTES * 4) // 3 + 8)


class UpdateCreate(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    source_entry_id: UUID | None = None
    photo: PhotoInput | None = None
    others_confirmed: bool = False

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Escribí la novedad.")
        return value


class WithdrawInput(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


class ConsentInput(BaseModel):
    given_by: str = Field(min_length=2, max_length=160)
    given_on: date

    @field_validator("given_by")
    @classmethod
    def clean_given_by(cls, value: str) -> str:
        return value.strip()


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


def _photos_visible(recipient: CareRecipient, settings: dict) -> bool:
    return settings["family_update_photos"] and recipient.image_consent_on is not None


def _photo_response(update: FamilyUpdate) -> Response:
    path = storage_dir() / update.photo_storage_key  # type: ignore[operator]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Foto no encontrada.")
    return Response(
        content=path.read_bytes(), media_type=update.photo_content_type,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


def _consent_read(recipient: CareRecipient) -> dict[str, str] | None:
    if recipient.image_consent_on is None:
        return None
    return {"given_by": recipient.image_consent_given_by or "", "given_on": recipient.image_consent_on.isoformat()}


def _staff_read(update: FamilyUpdate, account: UserAccount, manager: bool) -> dict[str, object]:
    return {
        "has_photo": update.photo_storage_key is not None,
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
    settings = settings_for(care_unit)
    return {
        "updates": [_staff_read(item, account, manager) for item in updates],
        "readers": sorted(m.user.display_name for m in _readers(session, recipient.id) if m.user.is_active),
        "can_publish": _can_publish(member, settings),
        "photos_enabled": settings["family_update_photos"],
        "image_consent": _consent_read(recipient),
        "can_manage_consent": bool(_roles(session, account, care_unit) & FAMILY_AUTHORIZER_ROLES),
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
    photo = _checked_photo(payload, recipient, settings) if payload.photo is not None else None
    update = FamilyUpdate(
        care_unit_id=care_unit.id, care_recipient_id=recipient.id, text=payload.text,
        source_entry_id=payload.source_entry_id, published_by_membership_id=member.id,
    )
    if photo is not None:
        update.photo_storage_key = uuid4().hex
        update.photo_content_type = payload.photo.content_type  # type: ignore[union-attr]
        fd = os.open(storage_dir() / update.photo_storage_key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(photo)
    session.add(update)
    session.flush()
    record_event(
        session, action="family_update.published", actor_account_id=account.id,
        organization_id=care_unit.organization_id, target_type="care_recipient", target_id=recipient.id,
        details={"update_id": str(update.id), "readers": len(readers), "photo": photo is not None},
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


def _checked_photo(payload: UpdateCreate, recipient: CareRecipient, settings: dict) -> bytes:
    if not settings["family_update_photos"]:
        raise HTTPException(status_code=422, detail="Este servicio no comparte fotos con las familias.")
    if recipient.image_consent_on is None:
        raise HTTPException(status_code=409, detail="Falta registrar el consentimiento de imagen de esta persona.")
    if not payload.others_confirmed:
        raise HTTPException(status_code=422, detail="Confirmá que en la foto no aparecen otras personas sin consentimiento.")
    assert payload.photo is not None
    try:
        content = base64.b64decode(payload.photo.data, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=422, detail="La foto no se pudo leer.") from None
    if len(content) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="La foto supera los 5 MB.")
    if not content.startswith(PHOTO_SIGNATURES[payload.photo.content_type]):
        raise HTTPException(status_code=415, detail="La foto debe ser JPG o PNG.")
    return content


@router.get("/{care_unit_id}/family-updates/{update_id}/photo")
def staff_photo(
    care_unit_id: UUID,
    update_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> Response:
    care_unit, _ = _unit_and_member(session, account, care_unit_id)
    update = session.scalar(select(FamilyUpdate).where(FamilyUpdate.id == update_id, FamilyUpdate.care_unit_id == care_unit.id))
    if update is None or update.photo_storage_key is None:
        raise HTTPException(status_code=404, detail="Foto no encontrada.")
    return _photo_response(update)


@router.put("/{care_unit_id}/care-recipients/{recipient_id}/image-consent")
def record_consent(
    care_unit_id: UUID,
    recipient_id: UUID,
    payload: ConsentInput,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> dict[str, object]:
    """Registra quién dio el consentimiento de imagen y cuándo (encargado, administrativo o médico)."""
    care_unit, member = _unit_and_member(session, account, care_unit_id)
    recipient = _active_recipient(session, care_unit, recipient_id)
    if not _roles(session, account, care_unit) & FAMILY_AUTHORIZER_ROLES:
        raise HTTPException(status_code=403, detail="Lo registra el encargado, un administrativo o el médico.")
    if payload.given_on > date.today():
        raise HTTPException(status_code=422, detail="La fecha del consentimiento no puede ser futura.")
    recipient.image_consent_given_by = payload.given_by
    recipient.image_consent_on = payload.given_on
    recipient.image_consent_recorded_by_membership_id = member.id
    record_event(
        session, action="image_consent.recorded", actor_account_id=account.id,
        organization_id=care_unit.organization_id, target_type="care_recipient", target_id=recipient.id,
    )
    session.commit()
    return {"image_consent": _consent_read(recipient)}


@router.delete("/{care_unit_id}/care-recipients/{recipient_id}/image-consent", status_code=204)
def revoke_consent(
    care_unit_id: UUID,
    recipient_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> Response:
    """Quita el consentimiento: la familia deja de ver las fotos ya publicadas."""
    care_unit, _ = _unit_and_member(session, account, care_unit_id)
    recipient = _active_recipient(session, care_unit, recipient_id)
    if not _roles(session, account, care_unit) & FAMILY_AUTHORIZER_ROLES:
        raise HTTPException(status_code=403, detail="Lo quita el encargado, un administrativo o el médico.")
    recipient.image_consent_given_by = None
    recipient.image_consent_on = None
    recipient.image_consent_recorded_by_membership_id = None
    record_event(
        session, action="image_consent.revoked", actor_account_id=account.id,
        organization_id=care_unit.organization_id, target_type="care_recipient", target_id=recipient.id,
    )
    session.commit()
    return Response(status_code=204)


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


def _allowed_recipients(memberships: list[OrganizationMembership]):
    return select(FamilyAuthorization.care_recipient_id).where(
        FamilyAuthorization.family_membership_id.in_([m.id for m in memberships]),
        FamilyAuthorization.category == SharedCareCategory.UPDATES,
        FamilyAuthorization.is_active.is_(True),
        FamilyAuthorization.can_view.is_(True),
    )


@family_router.get("/updates/{update_id}/photo")
def family_photo(
    update_id: UUID,
    session: Session = Depends(get_session),
    memberships: list[OrganizationMembership] = Depends(get_family_memberships),
) -> Response:
    update = session.scalar(
        select(FamilyUpdate).options(selectinload(FamilyUpdate.recipient)).where(
            FamilyUpdate.id == update_id,
            FamilyUpdate.withdrawn_at.is_(None),
            FamilyUpdate.photo_storage_key.is_not(None),
            FamilyUpdate.care_recipient_id.in_(_allowed_recipients(memberships)),
        )
    )
    care_unit = session.get(CareUnit, update.care_unit_id) if update is not None else None
    if update is None or care_unit is None or not update.recipient.is_active or not _photos_visible(update.recipient, settings_for(care_unit)):
        raise HTTPException(status_code=404, detail="Foto no encontrada.")
    return _photo_response(update)


@family_router.get("/updates")
def family_updates(
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
    memberships: list[OrganizationMembership] = Depends(get_family_memberships),
) -> list[dict[str, object]]:
    """Novedades vigentes de las personas que esta cuenta tiene autorizadas para "Novedades"."""
    allowed = _allowed_recipients(memberships)
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
            "has_photo": update.photo_storage_key is not None and _photos_visible(update.recipient, settings_for(unit)),
        }
        for update, unit in rows
    ]
