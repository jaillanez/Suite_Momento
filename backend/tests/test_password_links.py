"""Invitación y recuperación de contraseña por correo (modo local, sin envío real)."""

import re

import pytest
from fastapi.testclient import TestClient

from momento_api import mailer, password_links
from tests.access_helpers import PASSWORD, Scenario, as_user, client, scenario  # noqa: F401


@pytest.fixture(autouse=True)
def local_mail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOMENTO_SMTP_HOST", raising=False)
    monkeypatch.delenv("MOMENTO_MAIL_FROM", raising=False)
    mailer.outbox.clear()
    password_links._requests.clear()


def _token(message) -> str:
    return re.search(r"#restablecer=([\w-]+)", message.get_content()).group(1)


def test_reset_sends_link_and_new_password_works(client: TestClient, scenario: Scenario) -> None:
    response = client.post("/api/auth/password-reset/request", json={"email": "Medica@test.example"})
    assert response.status_code == 202
    assert len(mailer.outbox) == 1
    message = mailer.outbox[0]
    assert message["To"] == "medica@test.example"
    assert message["From"] == "illanezjorgea@gmail.com"

    token = _token(message)
    assert client.post("/api/auth/password-reset/confirm", json={"token": token, "password": "NuevaClave1"}).status_code == 204
    assert client.post("/api/auth/login", json={"email": "medica@test.example", "password": PASSWORD}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "medica@test.example", "password": "NuevaClave1"}).status_code == 200
    # El enlace sirve una sola vez.
    assert client.post("/api/auth/password-reset/confirm", json={"token": token, "password": "OtraClave12"}).status_code == 400


def test_reset_reply_is_the_same_for_unknown_accounts(client: TestClient, scenario: Scenario) -> None:
    known = client.post("/api/auth/password-reset/request", json={"email": "medica@test.example"})
    unknown = client.post("/api/auth/password-reset/request", json={"email": "nadie@test.example"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(mailer.outbox) == 1


def test_sender_can_be_changed_by_parameter(client: TestClient, scenario: Scenario, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOMENTO_MAIL_FROM", "avisos@momento.example")
    client.post("/api/auth/password-reset/request", json={"email": "medica@test.example"})
    assert mailer.outbox[0]["From"] == "avisos@momento.example"


def test_new_link_cancels_the_previous_one(client: TestClient, scenario: Scenario) -> None:
    client.post("/api/auth/password-reset/request", json={"email": "medica@test.example"})
    client.post("/api/auth/password-reset/request", json={"email": "medica@test.example"})
    first, second = (_token(m) for m in mailer.outbox)
    assert client.post("/api/auth/password-reset/confirm", json={"token": first, "password": "NuevaClave1"}).status_code == 400
    assert client.post("/api/auth/password-reset/confirm", json={"token": second, "password": "NuevaClave1"}).status_code == 204


def test_reset_requests_are_rate_limited(client: TestClient, scenario: Scenario) -> None:
    codes = [client.post("/api/auth/password-reset/request", json={"email": "x@test.example"}).status_code for _ in range(6)]
    assert codes[-1] == 429


def test_manager_invites_new_user_who_sets_password(client: TestClient, scenario: Scenario) -> None:
    manager = as_user(client, "jefa@test.example")
    created = manager.post(f"/api/organizations/{scenario.organization_id}/memberships", json={
        "display_name": "Nueva Cuidadora", "email": "nueva@test.example", "user_group": "staff",
        "care_unit_id": scenario.unit_id, "staff_role": "caregiver", "send_invitation": True,
    })
    assert created.status_code == 201
    assert len(mailer.outbox) == 1 and "Tu acceso a Momento" == mailer.outbox[0]["Subject"]
    # Sin contraseña, el pedido de recuperación no activa la cuenta.
    client.post("/api/auth/password-reset/request", json={"email": "nueva@test.example"})
    assert len(mailer.outbox) == 1

    token = _token(mailer.outbox[0])
    client.cookies.clear()
    assert client.post("/api/auth/password-reset/confirm", json={"token": token, "password": "Cuidadora1"}).status_code == 204
    assert client.post("/api/auth/login", json={"email": "nueva@test.example", "password": "Cuidadora1"}).status_code == 200


def test_invite_endpoint_is_manager_only(client: TestClient, scenario: Scenario) -> None:
    path = f"/api/organizations/{scenario.organization_id}/memberships/{scenario.memberships['caregiver']}/invite"
    assert as_user(client, "medica@test.example").post(path).status_code == 403
    client.cookies.clear()
    response = as_user(client, "jefa@test.example").post(path)
    assert response.status_code == 202
    assert mailer.outbox[-1]["To"] == "cuidador@test.example"


def test_invalid_token_or_short_password_is_rejected(client: TestClient, scenario: Scenario) -> None:
    assert client.post("/api/auth/password-reset/confirm", json={"token": "x" * 40, "password": "NuevaClave1"}).status_code == 400
    client.post("/api/auth/password-reset/request", json={"email": "medica@test.example"})
    token = _token(mailer.outbox[0])
    assert client.post("/api/auth/password-reset/confirm", json={"token": token, "password": "corta"}).status_code == 422
