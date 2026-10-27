from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from momento_api.auth import hash_password
from momento_api.main import app
from momento_api.models import (
    Base,
    Organization,
    OrganizationMembership,
    UserAccount,
    UserCredential,
    UserGroup,
)
from momento_api.session import get_session


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
        with sessions() as session:
            organization = Organization(name="Organización autenticada")
            staff = UserAccount(
                display_name="Encargada de prueba",
                email="encargada@example.test",
            )
            staff.memberships.append(
                OrganizationMembership(
                    organization=organization,
                    user_group=UserGroup.STAFF,
                    role_label="Encargada",
                )
            )
            family = UserAccount(
                display_name="Familiar de prueba",
                email="familia@example.test",
            )
            family.memberships.append(
                OrganizationMembership(
                    organization=organization,
                    user_group=UserGroup.FAMILY,
                    role_label="Familiar",
                )
            )
            session.add_all([organization, staff, family])
            session.flush()
            session.add_all([
                UserCredential(
                    user_account_id=staff.id,
                    password_hash=hash_password("ClaveSegura2026!"),
                ),
                UserCredential(
                    user_account_id=family.id,
                    password_hash=hash_password("ClaveFamiliar2026!"),
                ),
            ])
            session.commit()

        with TestClient(app) as client:
            login = client.post(
                "/api/auth/login",
                json={
                    "email": "encargada@example.test",
                    "password": "ClaveSegura2026!",
                },
            )
            assert login.status_code == 200
            yield client
    finally:
        app.dependency_overrides.pop(get_session, None)
        engine.dispose()
