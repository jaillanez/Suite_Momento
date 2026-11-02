"""Escenario compartido de permisos: una organización con dos sedes y un cuenta por puesto."""

from collections.abc import Generator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from momento_api.auth import hash_password
from momento_api.main import app
from momento_api.models import (
    CareRecipient,
    CareUnit,
    CareUnitType,
    CareUnitWorkflowStatus,
    Organization,
    OrganizationMembership,
    StaffRole,
    UserAccount,
    UserCredential,
    UserGroup,
)
from momento_api.session import get_session
from momento_api.workflow_defaults import DEFAULT_WORKFLOW_STATUSES

PASSWORD = "ClaveDePrueba2026!"


@dataclass
class Scenario:
    organization_id: str
    unit_id: str
    other_unit_id: str
    recipient_id: str
    other_recipient_id: str
    memberships: dict[str, str]


def _add_person(
    session: Session,
    organization: Organization,
    *,
    email: str,
    group: UserGroup,
    unit: CareUnit | None,
    role: StaffRole | None = None,
    inbox: bool = False,
) -> OrganizationMembership:
    account = UserAccount(display_name=email.split("@")[0].title(), email=email)
    session.add(account)
    session.flush()
    session.add(UserCredential(user_account_id=account.id, password_hash=hash_password(PASSWORD)))
    membership = OrganizationMembership(
        user_account_id=account.id,
        organization_id=organization.id,
        care_unit_id=unit.id if unit else None,
        user_group=group,
        staff_role=role,
        handles_inbox=inbox,
    )
    session.add(membership)
    session.flush()
    return membership


@pytest.fixture
def scenario(db_sessions: sessionmaker[Session]) -> Scenario:
    with db_sessions() as session:
        organization = Organization(name="Residencia de permisos")
        session.add(organization)
        session.flush()
        units = []
        for name in ("Sede Norte", "Sede Sur"):
            unit = CareUnit(
                organization_id=organization.id,
                name=name,
                service_type=CareUnitType.RESIDENCE,
                country_code="AR",
            )
            unit.workflow_statuses.extend(
                CareUnitWorkflowStatus(**item) for item in DEFAULT_WORKFLOW_STATUSES
            )
            session.add(unit)
            units.append(unit)
        session.flush()
        north, south = units
        recipient = CareRecipient(care_unit_id=north.id, display_name="Persona Norte")
        other_recipient = CareRecipient(care_unit_id=south.id, display_name="Persona Sur")
        session.add_all([recipient, other_recipient])

        people = {
            "manager": _add_person(session, organization, email="jefa@test.example", group=UserGroup.STAFF, unit=None, role=StaffRole.MANAGER),
            "physician": _add_person(session, organization, email="medica@test.example", group=UserGroup.STAFF, unit=north, role=StaffRole.PHYSICIAN),
            "physician_south": _add_person(session, organization, email="medicosur@test.example", group=UserGroup.STAFF, unit=south, role=StaffRole.PHYSICIAN),
            "caregiver": _add_person(session, organization, email="cuidador@test.example", group=UserGroup.STAFF, unit=north, role=StaffRole.CAREGIVER),
            "designated": _add_person(session, organization, email="bandeja@test.example", group=UserGroup.STAFF, unit=north, role=StaffRole.CAREGIVER, inbox=True),
            "designated_2": _add_person(session, organization, email="bandeja2@test.example", group=UserGroup.STAFF, unit=north, role=StaffRole.CAREGIVER, inbox=True),
            "family": _add_person(session, organization, email="familia@test.example", group=UserGroup.FAMILY, unit=north),
        }
        session.commit()
        return Scenario(
            organization_id=str(organization.id),
            unit_id=str(north.id),
            other_unit_id=str(south.id),
            recipient_id=str(recipient.id),
            other_recipient_id=str(other_recipient.id),
            memberships={key: str(value.id) for key, value in people.items()},
        )


@pytest.fixture
def client(db_sessions: sessionmaker[Session], scenario: Scenario) -> Generator[TestClient, None, None]:
    def override():
        with db_sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)


def as_user(client: TestClient, email: str, *, family: bool = False) -> TestClient:
    """Abre una sesión nueva por el login web; la cookie anterior se reemplaza."""
    client.cookies.clear()
    path = "/api/auth/family-login" if family else "/api/auth/login"
    response = client.post(path, json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return client


