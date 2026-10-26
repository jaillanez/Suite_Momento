from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from momento_api.main import app
from momento_api.models import Base, CareUnit, CareUnitType, Organization
from momento_api.session import get_session


def test_organization_can_hold_residential_and_home_care_services() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        organization = Organization(name="Organización de prueba")
        organization.care_units.extend(
            [
                CareUnit(
                    name="Residencia piloto",
                    service_type=CareUnitType.RESIDENCE,
                    country_code="AR",
                ),
                CareUnit(
                    name="Atención domiciliaria",
                    service_type=CareUnitType.HOME_CARE,
                    country_code="UY",
                ),
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


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    def override_get_session() -> Generator[Session, None, None]:
        with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)
        engine.dispose()


def test_api_creates_and_lists_organization(api_client: TestClient) -> None:
    created = api_client.post("/api/organizations", json={"name": "  Residencia Momento  "})

    assert created.status_code == 201
    assert created.json()["name"] == "Residencia Momento"
    assert created.headers["location"].startswith("/api/organizations/")

    listed = api_client.get("/api/organizations")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [created.json()["id"]]


def test_api_creates_care_unit_and_rejects_unknown_country(api_client: TestClient) -> None:
    organization = api_client.post(
        "/api/organizations",
        json={"name": "Residencia Momento"},
    ).json()
    organization_id = organization["id"]

    created = api_client.post(
        f"/api/organizations/{organization_id}/care-units",
        json={
            "name": "Sede Centro",
            "service_type": "residence",
            "country_code": "AR",
        },
    )
    assert created.status_code == 201
    assert created.json()["organization_id"] == organization_id

    listed = api_client.get(f"/api/organizations/{organization_id}/care-units")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    invalid = api_client.post(
        f"/api/organizations/{organization_id}/care-units",
        json={
            "name": "Servicio fuera de alcance",
            "service_type": "home_care",
            "country_code": "BR",
        },
    )
    assert invalid.status_code == 422


def test_api_returns_not_found_for_unknown_organization(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/organizations/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/care-units"
    )

    assert response.status_code == 404
