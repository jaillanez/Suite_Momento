"""Personas cuidadas: listado, alta y ficha completa con sus contactos."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from momento_api.access import find_staff_membership
from momento_api.audit import record_denied, record_event
from momento_api.auth import get_authenticated_account
from momento_api.models import (
    CareRecipient,
    CareRecipientContact,
    CareUnit,
    OrganizationMembership,
    StaffRole,
    UserAccount,
)
from momento_api.schemas import (
    HEALTH_FIELDS,
    CareRecipientContactInput,
    CareRecipientContactRead,
    CareRecipientCreate,
    CareRecipientProfileRead,
    CareRecipientProfileUpdate,
    CareRecipientRead,
)
from momento_api.session import get_session

router = APIRouter(prefix="/api/care-units", tags=["Personas cuidadas"])

# Quién edita la ficha. La salud la registran solo encargado y médico.
PROFILE_EDITORS = (StaffRole.MANAGER, StaffRole.ADMINISTRATIVE, StaffRole.PHYSICIAN)
HEALTH_EDITORS = (StaffRole.MANAGER, StaffRole.PHYSICIAN)


def _care_unit(session: Session, care_unit_id: UUID) -> CareUnit:
    care_unit = session.get(CareUnit, care_unit_id)
    if care_unit is None or not care_unit.is_active:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    return care_unit


def _viewer(session: Session, account: UserAccount, care_unit: CareUnit) -> OrganizationMembership:
    membership = find_staff_membership(
        session,
        account_id=account.id,
        organization_id=care_unit.organization_id,
        care_unit_id=care_unit.id,
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Servicio no encontrado.")
    return membership


def _roles(session: Session, account: UserAccount, care_unit: CareUnit) -> set[StaffRole]:
    """Todos los puestos con los que la cuenta alcanza el servicio."""
    return {
        role
        for role in session.scalars(
            select(OrganizationMembership.staff_role).where(
                OrganizationMembership.user_account_id == account.id,
                OrganizationMembership.organization_id == care_unit.organization_id,
                OrganizationMembership.is_active.is_(True),
                (OrganizationMembership.care_unit_id.is_(None))
                | (OrganizationMembership.care_unit_id == care_unit.id),
            )
        ).all()
        if role is not None
    }


def _deny(session: Session, account: UserAccount, care_unit: CareUnit, action: str, target_id: UUID | None, detail: str) -> HTTPException:
    record_denied(
        session,
        action=action,
        actor_account_id=account.id,
        organization_id=care_unit.organization_id,
        target_type="care_recipient",
        target_id=target_id,
    )
    return HTTPException(status_code=403, detail=detail)


def _recipient(session: Session, care_unit_id: UUID, recipient_id: UUID) -> CareRecipient:
    recipient = session.scalar(
        select(CareRecipient)
        .options(selectinload(CareRecipient.contacts))
        .where(CareRecipient.id == recipient_id, CareRecipient.care_unit_id == care_unit_id)
    )
    if recipient is None:
        raise HTTPException(status_code=404, detail="Persona cuidada no encontrada.")
    return recipient


def _profile(recipient: CareRecipient, roles: set[StaffRole]) -> CareRecipientProfileRead:
    profile = CareRecipientProfileRead.model_validate(recipient)
    profile.can_edit = bool(roles & set(PROFILE_EDITORS))
    profile.can_edit_health = bool(roles & set(HEALTH_EDITORS))
    profile.can_deactivate = StaffRole.MANAGER in roles
    return profile


@router.post(
    "/{care_unit_id}/care-recipients",
    response_model=CareRecipientRead,
    status_code=status.HTTP_201_CREATED,
)
def create_care_recipient(
    care_unit_id: UUID,
    payload: CareRecipientCreate,
    response: Response,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> CareRecipient:
    """Da de alta una persona; encargado o administrativo."""
    care_unit = _care_unit(session, care_unit_id)
    if not _roles(session, account, care_unit) & {StaffRole.MANAGER, StaffRole.ADMINISTRATIVE}:
        raise _deny(session, account, care_unit, "care_recipient.created", None,
                    "Solo el encargado o un administrativo pueden dar de alta personas.")

    recipient = CareRecipient(care_unit_id=care_unit_id, display_name=payload.display_name)
    session.add(recipient)
    session.flush()
    record_event(
        session,
        action="care_recipient.created",
        actor_account_id=account.id,
        organization_id=care_unit.organization_id,
        target_type="care_recipient",
        target_id=recipient.id,
    )
    session.commit()
    session.refresh(recipient)
    response.headers["Location"] = f"/api/care-units/{care_unit_id}/care-recipients/{recipient.id}"
    return recipient


@router.get("/{care_unit_id}/care-recipients", response_model=list[CareRecipientRead])
def list_care_recipients(
    care_unit_id: UUID,
    session: Session = Depends(get_session),
) -> list[CareRecipient]:
    """Lista las personas activas del servicio."""
    _care_unit(session, care_unit_id)
    statement = (
        select(CareRecipient)
        .where(CareRecipient.care_unit_id == care_unit_id, CareRecipient.is_active.is_(True))
        .order_by(CareRecipient.display_name, CareRecipient.id)
        .limit(500)
    )
    return list(session.scalars(statement).all())


@router.get(
    "/{care_unit_id}/care-recipients/{recipient_id}",
    response_model=CareRecipientProfileRead,
)
def read_care_recipient(
    care_unit_id: UUID,
    recipient_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> CareRecipientProfileRead:
    """Ficha completa; cada consulta queda registrada."""
    care_unit = _care_unit(session, care_unit_id)
    _viewer(session, account, care_unit)
    recipient = _recipient(session, care_unit_id, recipient_id)
    record_event(
        session,
        action="care_recipient.viewed",
        actor_account_id=account.id,
        organization_id=care_unit.organization_id,
        target_type="care_recipient",
        target_id=recipient.id,
    )
    session.commit()
    return _profile(recipient, _roles(session, account, care_unit))


@router.patch(
    "/{care_unit_id}/care-recipients/{recipient_id}",
    response_model=CareRecipientProfileRead,
)
def update_care_recipient(
    care_unit_id: UUID,
    recipient_id: UUID,
    payload: CareRecipientProfileUpdate,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> CareRecipientProfileRead:
    """Actualiza la ficha según el puesto de quien edita."""
    care_unit = _care_unit(session, care_unit_id)
    recipient = _recipient(session, care_unit_id, recipient_id)
    roles = _roles(session, account, care_unit)
    changes = payload.model_dump(exclude_unset=True)

    if not roles & set(PROFILE_EDITORS):
        raise _deny(session, account, care_unit, "care_recipient.updated", recipient.id,
                    "Solo encargado, administrativo o médico pueden editar la ficha.")
    if set(changes) & set(HEALTH_FIELDS) and not roles & set(HEALTH_EDITORS):
        raise _deny(session, account, care_unit, "care_recipient.updated", recipient.id,
                    "La información de salud la registran el encargado o el médico.")
    if "is_active" in changes and StaffRole.MANAGER not in roles:
        raise _deny(session, account, care_unit, "care_recipient.updated", recipient.id,
                    "Solo el encargado puede dar de baja a una persona.")

    changed = [field for field, value in changes.items() if getattr(recipient, field) != value]
    for field in changed:
        setattr(recipient, field, changes[field])
    if changed:
        record_event(
            session,
            action="care_recipient.updated",
            actor_account_id=account.id,
            organization_id=care_unit.organization_id,
            target_type="care_recipient",
            target_id=recipient.id,
            details={"fields": sorted(changed)},
        )
        session.commit()
        recipient = _recipient(session, care_unit_id, recipient_id)
    return _profile(recipient, roles)


def _require_contact_editor(session: Session, account: UserAccount, care_unit: CareUnit, recipient: CareRecipient) -> None:
    if not _roles(session, account, care_unit) & set(PROFILE_EDITORS):
        raise _deny(session, account, care_unit, "care_recipient.contacts_changed", recipient.id,
                    "Solo encargado, administrativo o médico pueden editar contactos.")


def _record_contacts_change(session: Session, account: UserAccount, care_unit: CareUnit, recipient: CareRecipient, change: str) -> None:
    record_event(
        session,
        action="care_recipient.contacts_changed",
        actor_account_id=account.id,
        organization_id=care_unit.organization_id,
        target_type="care_recipient",
        target_id=recipient.id,
        details={"change": change},
    )


@router.post(
    "/{care_unit_id}/care-recipients/{recipient_id}/contacts",
    response_model=CareRecipientContactRead,
    status_code=status.HTTP_201_CREATED,
)
def add_contact(
    care_unit_id: UUID,
    recipient_id: UUID,
    payload: CareRecipientContactInput,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> CareRecipientContact:
    care_unit = _care_unit(session, care_unit_id)
    recipient = _recipient(session, care_unit_id, recipient_id)
    _require_contact_editor(session, account, care_unit, recipient)
    contact = CareRecipientContact(care_recipient_id=recipient.id, **payload.model_dump())
    session.add(contact)
    _record_contacts_change(session, account, care_unit, recipient, "added")
    session.commit()
    session.refresh(contact)
    return contact


def _contact(session: Session, recipient: CareRecipient, contact_id: UUID) -> CareRecipientContact:
    contact = session.get(CareRecipientContact, contact_id)
    if contact is None or contact.care_recipient_id != recipient.id:
        raise HTTPException(status_code=404, detail="Contacto no encontrado.")
    return contact


@router.put(
    "/{care_unit_id}/care-recipients/{recipient_id}/contacts/{contact_id}",
    response_model=CareRecipientContactRead,
)
def update_contact(
    care_unit_id: UUID,
    recipient_id: UUID,
    contact_id: UUID,
    payload: CareRecipientContactInput,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> CareRecipientContact:
    care_unit = _care_unit(session, care_unit_id)
    recipient = _recipient(session, care_unit_id, recipient_id)
    _require_contact_editor(session, account, care_unit, recipient)
    contact = _contact(session, recipient, contact_id)
    for field, value in payload.model_dump().items():
        setattr(contact, field, value)
    _record_contacts_change(session, account, care_unit, recipient, "updated")
    session.commit()
    session.refresh(contact)
    return contact


@router.delete(
    "/{care_unit_id}/care-recipients/{recipient_id}/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_contact(
    care_unit_id: UUID,
    recipient_id: UUID,
    contact_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> Response:
    care_unit = _care_unit(session, care_unit_id)
    recipient = _recipient(session, care_unit_id, recipient_id)
    _require_contact_editor(session, account, care_unit, recipient)
    session.delete(_contact(session, recipient, contact_id))
    _record_contacts_change(session, account, care_unit, recipient, "removed")
    session.commit()
    return Response(status_code=204)
