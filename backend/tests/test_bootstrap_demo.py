from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from momento_api.bootstrap_demo import add_membership
from momento_api.models import (
    Base,
    CareUnit,
    CareUnitType,
    Organization,
    UserAccount,
    UserGroup,
)


def test_demo_manager_membership_persists_organization_id() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        organization = Organization(name="Residencia de prueba")
        session.add(organization)
        session.flush()

        unit = CareUnit(
            organization_id=organization.id,
            name="Sede de prueba",
            service_type=CareUnitType.RESIDENCE,
            country_code="AR",
        )
        manager = UserAccount(display_name="Encargado de prueba")
        session.add_all([unit, manager])
        session.flush()

        membership = add_membership(
            session,
            user_account_id=manager.id,
            organization_id=organization.id,
            care_unit_id=None,
            user_group=UserGroup.STAFF,
            role_label="Encargado de residencia",
        )
        session.commit()

        stored = session.get(type(membership), membership.id)
        assert stored is not None
        assert stored.user_account_id == manager.id
        assert stored.organization_id == organization.id
        assert stored.care_unit_id is None

    engine.dispose()
