"""Otorgamiento y revocación del acceso familiar por persona y categoría."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from momento_api.access import find_staff_membership
from momento_api.audit import record_denied, record_event
from momento_api.auth import get_authenticated_account
from momento_api.models import (
    FAMILY_AUTHORIZER_ROLES,
    CareRecipient,
    CareUnit,
    FamilyAuthorization,
    OrganizationMembership,
    UserAccount,
    UserGroup,
)
from momento_api.schemas import FamilyAuthorizationGrant, FamilyAuthorizationRead
from momento_api.session import get_session

router = APIRouter(
    prefix="/api/organizations/{organization_id}/family-authorizations",
    tags=["Autorizaciones familiares"],
)

_DENIED = "La acción requiere el puesto de encargado, administrativo o médico."


def _recipient_in_organization(
    session: Session, organization_id: UUID, care_recipient_id: UUID
) -> CareRecipient:
    recipient = session.scalar(
        select(CareRecipient)
        .join(CareUnit, CareUnit.id == CareRecipient.care_unit_id)
        .where(
            CareRecipient.id == care_recipient_id,
            CareRecipient.is_active.is_(True),
            CareUnit.organization_id == organization_id,
            CareUnit.is_active.is_(True),
        )
    )
    if recipient is None:
        raise HTTPException(status_code=404, detail="Persona cuidada no encontrada.")
    return recipient


def _require_authorizer(
    session: Session,
    account: UserAccount,
    organization_id: UUID,
    care_unit_id: UUID | None,
    *,
    action: str,
    target_id: UUID | None = None,
) -> OrganizationMembership:
    membership = find_staff_membership(
        session,
        account_id=account.id,
        organization_id=organization_id,
        care_unit_id=care_unit_id,
        roles=FAMILY_AUTHORIZER_ROLES,
    )
    if membership is None:
        record_denied(
            session,
            action=action,
            actor_account_id=account.id,
            organization_id=organization_id,
            target_type="care_recipient" if target_id else None,
            target_id=target_id,
        )
        raise HTTPException(status_code=403, detail=_DENIED)
    return membership


@router.get("", response_model=list[FamilyAuthorizationRead])
def list_family_authorizations(
    organization_id: UUID,
    care_recipient_id: UUID | None = Query(default=None),
    family_membership_id: UUID | None = Query(default=None),
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> list[FamilyAuthorization]:
    """Lista autorizaciones activas dentro del alcance de quien consulta."""
    authorizer = _require_authorizer(
        session, account, organization_id, None, action="family_authorization.listed"
    )
    statement = (
        select(FamilyAuthorization)
        .join(CareRecipient, CareRecipient.id == FamilyAuthorization.care_recipient_id)
        .join(CareUnit, CareUnit.id == CareRecipient.care_unit_id)
        .where(
            CareUnit.organization_id == organization_id,
            FamilyAuthorization.is_active.is_(True),
        )
    )
    if authorizer.care_unit_id is not None:
        statement = statement.where(CareUnit.id == authorizer.care_unit_id)
    if care_recipient_id is not None:
        statement = statement.where(FamilyAuthorization.care_recipient_id == care_recipient_id)
    if family_membership_id is not None:
        statement = statement.where(
            FamilyAuthorization.family_membership_id == family_membership_id
        )
    statement = statement.order_by(FamilyAuthorization.granted_at, FamilyAuthorization.id)
    return list(session.scalars(statement.limit(500)).all())


@router.post("", response_model=list[FamilyAuthorizationRead])
def grant_family_authorization(
    organization_id: UUID,
    payload: FamilyAuthorizationGrant,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> list[FamilyAuthorization]:
    """Habilita una o más categorías; la familia consulta, responde y solicita."""
    recipient = _recipient_in_organization(session, organization_id, payload.care_recipient_id)
    authorizer = _require_authorizer(
        session,
        account,
        organization_id,
        recipient.care_unit_id,
        action="family_authorization.granted",
        target_id=recipient.id,
    )
    family = session.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.id == payload.family_membership_id,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_group == UserGroup.FAMILY,
            OrganizationMembership.is_active.is_(True),
            or_(
                OrganizationMembership.care_unit_id.is_(None),
                OrganizationMembership.care_unit_id == recipient.care_unit_id,
            ),
        )
    )
    if family is None:
        raise HTTPException(
            status_code=422,
            detail="La cuenta familiar no está activa en el servicio de esta persona.",
        )

    existing = {
        item.category: item
        for item in session.scalars(
            select(FamilyAuthorization).where(
                FamilyAuthorization.family_membership_id == family.id,
                FamilyAuthorization.care_recipient_id == recipient.id,
            )
        ).all()
    }
    granted: list[str] = []
    for category in payload.categories:
        record = existing.get(category)
        if record is not None and record.is_active:
            continue
        if record is None:
            record = FamilyAuthorization(
                care_recipient_id=recipient.id,
                family_membership_id=family.id,
                category=category,
            )
            session.add(record)
        record.authorized_by_membership_id = authorizer.id
        record.can_view = True
        record.can_respond = True
        record.can_request = True
        record.is_active = True
        record.granted_at = datetime.now(timezone.utc)
        record.revoked_at = None
        record.revoked_by_membership_id = None
        granted.append(category.value)

    if granted:
        session.flush()
        record_event(
            session,
            action="family_authorization.granted",
            actor_account_id=account.id,
            organization_id=organization_id,
            target_type="care_recipient",
            target_id=recipient.id,
            details={
                "family_membership_id": str(family.id),
                "categories": granted,
            },
        )
        session.commit()

    return list(
        session.scalars(
            select(FamilyAuthorization)
            .where(
                FamilyAuthorization.family_membership_id == family.id,
                FamilyAuthorization.care_recipient_id == recipient.id,
                FamilyAuthorization.is_active.is_(True),
            )
            .order_by(FamilyAuthorization.category)
        ).all()
    )


@router.post("/{authorization_id}/revoke", response_model=FamilyAuthorizationRead)
def revoke_family_authorization(
    organization_id: UUID,
    authorization_id: UUID,
    session: Session = Depends(get_session),
    account: UserAccount = Depends(get_authenticated_account),
) -> FamilyAuthorization:
    """Retira una categoría; deja de habilitar el acceso de inmediato."""
    authorization = session.get(FamilyAuthorization, authorization_id)
    if authorization is None:
        raise HTTPException(status_code=404, detail="Autorización no encontrada.")
    recipient = _recipient_in_organization(
        session, organization_id, authorization.care_recipient_id
    )
    authorizer = _require_authorizer(
        session,
        account,
        organization_id,
        recipient.care_unit_id,
        action="family_authorization.revoked",
        target_id=recipient.id,
    )
    if authorization.is_active:
        authorization.is_active = False
        authorization.revoked_at = datetime.now(timezone.utc)
        authorization.revoked_by_membership_id = authorizer.id
        record_event(
            session,
            action="family_authorization.revoked",
            actor_account_id=account.id,
            organization_id=organization_id,
            target_type="family_authorization",
            target_id=authorization.id,
            details={"category": authorization.category.value},
        )
        session.commit()
        session.refresh(authorization)
    return authorization
