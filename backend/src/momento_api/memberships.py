"""Gestión local de cuentas y vínculos organizativos de prueba."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from momento_api.auth import get_organization_admin_account
from momento_api.models import (
    CareUnit,
    Organization,
    OrganizationMembership,
    UserAccount,
)
from momento_api.schemas import MembershipCreate, OrganizationMembershipRead
from momento_api.session import get_session

router = APIRouter(prefix="/api/organizations", tags=["Usuarios y membresías"])


@router.post(
    "/{organization_id}/memberships",
    response_model=OrganizationMembershipRead,
    dependencies=[Depends(get_organization_admin_account)],
    status_code=status.HTTP_201_CREATED,
)
def create_membership(
    organization_id: UUID,
    payload: MembershipCreate,
    response: Response,
    session: Session = Depends(get_session),
) -> OrganizationMembership:
    """Crea una cuenta de prueba y la vincula con la organización o servicio."""
    organization = session.get(Organization, organization_id)
    if organization is None or not organization.is_active:
        raise HTTPException(status_code=404, detail="Organización no encontrada.")

    care_unit = None
    if payload.care_unit_id is not None:
        care_unit = session.get(CareUnit, payload.care_unit_id)
        if (
            care_unit is None
            or not care_unit.is_active
            or care_unit.organization_id != organization_id
        ):
            raise HTTPException(
                status_code=422,
                detail="El servicio no pertenece a esta organización activa.",
            )

    account = UserAccount(
        display_name=payload.display_name,
        email=payload.email,
        phone=payload.phone,
    )
    membership = OrganizationMembership(
        user=account,
        organization=organization,
        care_unit=care_unit,
        user_group=payload.user_group,
        role_label=payload.role_label,
    )
    session.add(membership)
    session.commit()
    session.refresh(membership)
    response.headers["Location"] = (
        f"/api/organizations/{organization_id}/memberships/{membership.id}"
    )
    return membership


@router.get(
    "/{organization_id}/memberships",
    response_model=list[OrganizationMembershipRead],
    dependencies=[Depends(get_organization_admin_account)],
)
def list_memberships(
    organization_id: UUID,
    limit: int = Query(default=100, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[OrganizationMembership]:
    """Lista cuentas activas vinculadas a la organización."""
    organization = session.get(Organization, organization_id)
    if organization is None or not organization.is_active:
        raise HTTPException(status_code=404, detail="Organización no encontrada.")

    statement = (
        select(OrganizationMembership)
        .options(joinedload(OrganizationMembership.user))
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.is_active.is_(True),
        )
        .order_by(OrganizationMembership.created_at, OrganizationMembership.id)
        .limit(limit)
    )
    return list(session.scalars(statement).all())
