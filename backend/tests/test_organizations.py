from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from momento_api.models import Base, CareUnit, CareUnitType, Organization


def test_organization_can_hold_residential_and_home_care_services() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        organization = Organization(name="Organización de prueba")
        organization.care_units.extend(
            [
                CareUnit(name="Residencia piloto", service_type=CareUnitType.RESIDENCE, country_code="AR"),
                CareUnit(name="Atención domiciliaria", service_type=CareUnitType.HOME_CARE, country_code="UY"),
            ]
        )
        session.add(organization)
        session.commit()

        stored = session.get(Organization, organization.id)

        assert stored is not None
        assert {unit.service_type for unit in stored.care_units} == {
            CareUnitType.RESIDENCE,
            CareUnitType.HOME_CARE,
        }
        assert {unit.country_code for unit in stored.care_units} == {"AR", "UY"}

    engine.dispose()
