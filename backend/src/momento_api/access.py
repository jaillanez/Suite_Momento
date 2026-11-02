"""Reglas de alcance del personal según puesto, organización y servicio."""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from momento_api.models import OrganizationMembership, StaffRole, UserGroup


def find_staff_membership(
    session: Session,
    *,
    account_id: UUID,
    organization_id: UUID,
    care_unit_id: UUID | None = None,
    roles: Iterable[StaffRole] | None = None,
    inbox: bool = False,
) -> OrganizationMembership | None:
    """Devuelve el vínculo de personal activo que alcanza el servicio pedido.

    Un vínculo sin servicio alcanza a toda la organización. ``roles`` limita
    los puestos aceptados; ``inbox`` exige ser encargado o personal designado
    para la bandeja. Se prefiere el vínculo de alcance más amplio.
    """
    statement = select(OrganizationMembership).where(
        OrganizationMembership.user_account_id == account_id,
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.user_group == UserGroup.STAFF,
        OrganizationMembership.is_active.is_(True),
    )
    if care_unit_id is not None:
        statement = statement.where(
            or_(
                OrganizationMembership.care_unit_id.is_(None),
                OrganizationMembership.care_unit_id == care_unit_id,
            )
        )
    if roles is not None:
        statement = statement.where(OrganizationMembership.staff_role.in_(list(roles)))
    if inbox:
        statement = statement.where(
            or_(
                OrganizationMembership.staff_role == StaffRole.MANAGER,
                OrganizationMembership.handles_inbox.is_(True),
            )
        )
    statement = statement.order_by(
        OrganizationMembership.care_unit_id.is_(None).desc(),
        OrganizationMembership.created_at,
    )
    return session.scalars(statement.limit(1)).first()
