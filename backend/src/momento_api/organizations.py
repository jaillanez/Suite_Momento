"""Operaciones iniciales para organizaciones y servicios de cuidado."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from momento_api.models import CareUnit, CareUnitWorkflowStatus, Organization, OrganizationMembership, UserAccount, UserGroup
from momento_api.auth import get_management_account
from momento_api.workflow_defaults import DEFAULT_WORKFLOW_STATUSES
from momento_api.schemas import (
    CareUnitCreate,
    CareUnitRead,
    OrganizationCreate,
    OrganizationRead,
)
from momento_api.session import get_session

router = APIRouter(prefix="/api/organizations", tags=["Organizaciones"])


@router.post(
    "",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(
    payload: OrganizationCreate,
    response: Response,
    session: Session = Depends(get_session),
    current_user: UserAccount = Depends(get_management_account),
) -> Organization:
    """Crea una organización y vincula a quien la inició como personal gestor."""
    organization = Organization(name=payload.name)
    organization.memberships.append(OrganizationMembership(
        user_account_id=current_user.id,
        user_group=UserGroup.STAFF,
        role_label="Encargado/a",
    ))
    session.add(organization)
    session.commit()
    session.refresh(organization)
    response.headers["Location"] = f"/api/organizations/{organization.id}"
    return organization


@router.get("", response_model=list[OrganizationRead])
def list_organizations(
    limit: int = Query(default=100, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: UserAccount = Depends(get_management_account),
) -> list[Organization]:
    """Lista solo organizaciones donde la cuenta tiene un vínculo activo de personal."""
    member_organizations = select(OrganizationMembership.organization_id).where(
        OrganizationMembership.user_account_id == current_user.id,
        OrganizationMembership.is_active.is_(True),
        OrganizationMembership.user_group == UserGroup.STAFF,
    )
    statement = (
        select(Organization)
        .where(Organization.is_active.is_(True), Organization.id.in_(member_organizations))
        .order_by(Organization.name, Organization.id)
        .limit(limit)
    )
    return list(session.scalars(statement).all())


@router.post(
    "/{organization_id}/care-units",
    response_model=CareUnitRead,
    status_code=status.HTTP_201_CREATED,
)
def create_care_unit(
    organization_id: UUID,
    payload: CareUnitCreate,
    response: Response,
    session: Session = Depends(get_session),
) -> CareUnit:
    """Agrega una residencia o servicio domiciliario a una organización."""
    organization = session.get(Organization, organization_id)
    if organization is None or not organization.is_active:
        raise HTTPException(status_code=404, detail="Organización no encontrada.")

    care_unit = CareUnit(
        organization_id=organization_id,
        name=payload.name,
        service_type=payload.service_type,
        country_code=payload.country_code,
    )
    care_unit.workflow_statuses.extend(
        CareUnitWorkflowStatus(**item) for item in DEFAULT_WORKFLOW_STATUSES
    )
    session.add(care_unit)
    session.commit()
    session.refresh(care_unit)
    response.headers["Location"] = (
        f"/api/organizations/{organization_id}/care-units/{care_unit.id}"
    )
    return care_unit


@router.get(
    "/{organization_id}/care-units",
    response_model=list[CareUnitRead],
)
def list_care_units(
    organization_id: UUID,
    limit: int = Query(default=100, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[CareUnit]:
    """Lista los servicios de una organización activa."""
    organization = session.get(Organization, organization_id)
    if organization is None or not organization.is_active:
        raise HTTPException(status_code=404, detail="Organización no encontrada.")

    statement = (
        select(CareUnit)
        .where(
            CareUnit.organization_id == organization_id,
            CareUnit.is_active.is_(True),
        )
        .order_by(CareUnit.name, CareUnit.id)
        .limit(limit)
    )
    return list(session.scalars(statement).all())
