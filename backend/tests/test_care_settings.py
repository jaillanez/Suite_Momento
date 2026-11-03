"""Configuración del registro del cuidado por servicio."""

import copy
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from momento_api import mailer
from momento_api.care_log import shift_at
from momento_api.care_settings import DEFAULTS, SHIFT_PRESETS, clean_settings
from tests.access_helpers import Scenario, as_user, client, scenario  # noqa: F401

AR = ZoneInfo("America/Argentina/Buenos_Aires")


def _put(s: Scenario) -> str:
    return f"/api/organizations/{s.organization_id}/care-units/{s.unit_id}/care-settings"


def _entries(s: Scenario) -> str:
    return f"/api/care-units/{s.unit_id}/care-recipients/{s.recipient_id}/care-entries"


def _settings(**changes) -> dict:
    data = copy.deepcopy(DEFAULTS)
    data.update(changes)
    return data


def test_two_twelve_hour_shifts() -> None:
    shifts = SHIFT_PRESETS["2x12"]
    assert shift_at(datetime(2026, 11, 3, 9, tzinfo=AR), AR, shifts)["label"] == "Día"
    night = shift_at(datetime(2026, 11, 4, 2, tzinfo=AR), AR, shifts)
    assert night["label"] == "Noche" and night["start"] == datetime(2026, 11, 3, 20, tzinfo=AR)


def test_validation_rejects_bad_settings() -> None:
    with pytest.raises(ValueError):
        clean_settings(_settings(shifts=[{"label": "A", "start_hour": 6}, {"label": "B", "start_hour": 6}]))
    with pytest.raises(ValueError):
        clean_settings(_settings(shifts=[{"label": "A", "start_hour": 24}]))
    # Aunque se desactiven todos, "Incidente" queda habilitado.
    all_off = clean_settings(_settings(categories=[{**c, "enabled": False} for c in DEFAULTS["categories"]]))
    assert [c["code"] for c in all_off["categories"] if c["enabled"]] == ["incident"]
    with pytest.raises(ValueError):
        clean_settings(_settings(incident_notify_roles=["dueño"]))
    with pytest.raises(ValueError):
        clean_settings({**DEFAULTS, "inventado": 1})
    assert clean_settings(_settings(shifts=[{"label": " Noche ", "start_hour": 20}, {"label": "Día", "start_hour": 8}]))["shifts"][0] == {"label": "Día", "start_hour": 8}


def test_only_organization_manager_changes_settings(client: TestClient, scenario: Scenario) -> None:
    assert as_user(client, "medica@test.example").put(_put(scenario), json=DEFAULTS).status_code == 403
    client.cookies.clear()
    manager = as_user(client, "jefa@test.example")
    response = manager.put(_put(scenario), json=_settings(shifts=SHIFT_PRESETS["2x12"]))
    assert response.status_code == 200
    assert manager.get(f"/api/care-units/{scenario.unit_id}/care-settings").json()["shifts"] == SHIFT_PRESETS["2x12"]
    handover = manager.get(f"/api/care-units/{scenario.unit_id}/handover").json()
    assert handover["current_shift"]["label"] in {"Día", "Noche"}


def test_disabled_category_renamed_label_and_backdate(client: TestClient, scenario: Scenario) -> None:
    categories = [
        {**c, "enabled": c["code"] != "sleep", "label": "Comidas" if c["code"] == "food" else c["label"]}
        for c in DEFAULTS["categories"]
    ]
    manager = as_user(client, "jefa@test.example")
    manager.put(_put(scenario), json=_settings(categories=categories, max_backdate_days=0))
    client.cookies.clear()
    caregiver = as_user(client, "cuidador@test.example")
    assert caregiver.post(_entries(scenario), json={"category": "sleep", "text": "x"}).status_code == 422
    created = caregiver.post(_entries(scenario), json={"category": "food", "text": "Almorzó"}).json()
    assert created["category_label"] == "Comidas"
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert caregiver.post(_entries(scenario), json={"category": "food", "text": "x", "occurred_at": yesterday}).status_code == 422
    codes = [c["code"] for c in caregiver.get(_entries(scenario)).json()["settings"]["categories"]]
    assert "sleep" not in codes


def test_incident_rules_follow_settings(client: TestClient, scenario: Scenario, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOMENTO_SMTP_HOST", raising=False)
    monkeypatch.setenv("MOMENTO_MAIL_DEBUG", "true")
    mailer.outbox.clear()
    manager = as_user(client, "jefa@test.example")
    manager.put(_put(scenario), json=_settings(
        incident_always_important=False, incident_void="author", incident_notify_roles=["manager", "physician"],
        incident_notify_email=True,
    ))
    client.cookies.clear()
    caregiver = as_user(client, "cuidador@test.example")
    entry = caregiver.post(_entries(scenario), json={"category": "incident", "text": "Se cayó en el pasillo"}).json()
    assert entry["important"] is False and entry["can_void"] is True
    assert sorted(m["To"] for m in mailer.outbox) == ["jefa@test.example", "medica@test.example"]
    body = mailer.outbox[0].get_content()
    assert "Se cayó" not in body and "Persona Norte" not in body
    assert caregiver.post(f"/api/care-units/{scenario.unit_id}/care-entries/{entry['id']}/void", json={"reason": "Error"}).status_code == 200


def test_no_incident_email_when_roles_empty(client: TestClient, scenario: Scenario, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOMENTO_MAIL_DEBUG", "true")
    mailer.outbox.clear()
    as_user(client, "jefa@test.example").put(_put(scenario), json=_settings(incident_notify_roles=[]))
    client.cookies.clear()
    as_user(client, "cuidador@test.example").post(_entries(scenario), json={"category": "incident", "text": "x"})
    assert mailer.outbox == []


def test_incident_category_cannot_be_disabled_or_impersonated() -> None:
    hidden = [{**c, "enabled": c["code"] != "incident", "label": "Caída" if c["code"] == "incident" else c["label"]} for c in DEFAULTS["categories"]]
    incident = next(c for c in clean_settings(_settings(categories=hidden))["categories"] if c["code"] == "incident")
    assert incident == {"code": "incident", "label": "Incidente", "enabled": True}
    fake = [{**c, "label": "incidente" if c["code"] == "other" else c["label"]} for c in DEFAULTS["categories"]]
    with pytest.raises(ValueError):
        clean_settings(_settings(categories=fake))


def test_incident_creates_in_app_notification_and_email_is_optional(client: TestClient, scenario: Scenario, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOMENTO_MAIL_DEBUG", "true")
    mailer.outbox.clear()
    as_user(client, "cuidador@test.example").post(_entries(scenario), json={"category": "incident", "text": "Se cayó"})
    assert mailer.outbox == []  # por defecto, solo aviso en Momento
    client.cookies.clear()
    manager = as_user(client, "jefa@test.example")
    data = manager.get("/api/notifications").json()
    assert data["unread"] == 1
    item = data["items"][0]
    assert item["kind"] == "incident" and "Persona Norte" in item["title"] and "Se cayó" not in (item["body"] or "")
    assert manager.post(f"/api/notifications/{item['id']}/read").status_code == 204
    assert manager.get("/api/notifications").json()["unread"] == 0
    client.cookies.clear()
    # Otra cuenta no ve ni marca avisos ajenos.
    other = as_user(client, "medica@test.example")
    assert other.get("/api/notifications").json()["items"] == []
    assert other.post(f"/api/notifications/{item['id']}/read").status_code == 404


def test_notifications_hidden_after_moving_to_another_unit(client: TestClient, scenario: Scenario) -> None:
    put = _put(scenario)
    manager = as_user(client, "jefa@test.example")
    manager.put(put, json=_settings(incident_notify_roles=["physician"]))
    client.cookies.clear()
    as_user(client, "cuidador@test.example").post(_entries(scenario), json={"category": "incident", "text": "x"})
    client.cookies.clear()
    physician = as_user(client, "medica@test.example")
    assert physician.get("/api/notifications").json()["unread"] == 1
    from momento_api.models import OrganizationMembership
    from momento_api.session import get_session
    from uuid import UUID
    session = next(client.app.dependency_overrides[get_session]())
    member = session.get(OrganizationMembership, UUID(scenario.memberships["physician"]))
    member.care_unit_id = UUID(scenario.other_unit_id)
    session.commit()
    assert physician.get("/api/notifications").json() == {"unread": 0, "items": []}
