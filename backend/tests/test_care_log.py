"""Registro diario, pendientes y entrega de turno."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from momento_api.care_log import shift_at
from tests.access_helpers import Scenario, as_user, client, scenario  # noqa: F401

AR = ZoneInfo("America/Argentina/Buenos_Aires")


def _entries(s: Scenario) -> str:
    return f"/api/care-units/{s.unit_id}/care-recipients/{s.recipient_id}/care-entries"


def test_shifts_cover_the_whole_day_including_night() -> None:
    assert shift_at(datetime(2026, 11, 3, 6, 0, tzinfo=AR), AR)["label"] == "Mañana"
    assert shift_at(datetime(2026, 11, 3, 13, 59, tzinfo=AR), AR)["label"] == "Mañana"
    assert shift_at(datetime(2026, 11, 3, 14, 0, tzinfo=AR), AR)["label"] == "Tarde"
    night = shift_at(datetime(2026, 11, 4, 3, 0, tzinfo=AR), AR)
    assert night["label"] == "Noche"
    assert night["start"] == datetime(2026, 11, 3, 22, 0, tzinfo=AR)
    assert night["end"] == datetime(2026, 11, 4, 6, 0, tzinfo=AR)


def test_caregiver_records_and_entry_reaches_handover(client: TestClient, scenario: Scenario) -> None:
    caregiver = as_user(client, "cuidador@test.example")
    created = caregiver.post(_entries(scenario), json={"category": "food", "text": "Almorzó todo", "important": True})
    assert created.status_code == 201, created.text
    assert created.json()["recorded_by_name"] == "Cuidador"
    assert created.json()["can_void"] is True

    listed = caregiver.get(_entries(scenario)).json()
    assert [e["text"] for e in listed["entries"]] == ["Almorzó todo"]
    handover = caregiver.get(f"/api/care-units/{scenario.unit_id}/handover").json()
    assert handover["current_shift"]["label"] in {"Mañana", "Tarde", "Noche"}
    assert [e["text"] for e in handover["entries"]] == ["Almorzó todo"]


def test_entries_cannot_be_future_or_too_old(client: TestClient, scenario: Scenario) -> None:
    caregiver = as_user(client, "cuidador@test.example")
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    assert caregiver.post(_entries(scenario), json={"category": "sleep", "text": "x", "occurred_at": future}).status_code == 422
    assert caregiver.post(_entries(scenario), json={"category": "sleep", "text": "x", "occurred_at": old}).status_code == 422
    assert caregiver.post(_entries(scenario), json={"category": "inventada", "text": "x"}).status_code == 422


def test_only_author_or_manager_can_void_and_voided_stays_visible(client: TestClient, scenario: Scenario) -> None:
    entry = as_user(client, "cuidador@test.example").post(_entries(scenario), json={"category": "mood", "text": "Triste"}).json()
    void = f"/api/care-units/{scenario.unit_id}/care-entries/{entry['id']}/void"
    client.cookies.clear()
    other = as_user(client, "bandeja@test.example")
    assert other.get(_entries(scenario)).json()["entries"][0]["can_void"] is False
    assert other.post(void, json={"reason": "Error de persona"}).status_code == 403
    client.cookies.clear()
    manager = as_user(client, "jefa@test.example")
    voided = manager.post(void, json={"reason": "Era de otra persona"})
    assert voided.status_code == 200 and voided.json()["voided"] is True
    assert manager.post(void, json={"reason": "otra vez"}).status_code == 409
    listed = manager.get(_entries(scenario)).json()["entries"]
    assert listed[0]["voided"] is True and listed[0]["void_reason"] == "Era de otra persona"
    # Lo anulado no aparece en la entrega de turno.
    assert manager.get(f"/api/care-units/{scenario.unit_id}/handover").json()["entries"] == []


def test_other_unit_staff_and_family_cannot_see_log(client: TestClient, scenario: Scenario) -> None:
    as_user(client, "cuidador@test.example").post(_entries(scenario), json={"category": "health", "text": "Tos"})
    client.cookies.clear()
    south = as_user(client, "medicosur@test.example")
    assert south.get(_entries(scenario)).status_code == 404
    assert south.get(f"/api/care-units/{scenario.unit_id}/handover").status_code == 404
    other_recipient = f"/api/care-units/{scenario.unit_id}/care-recipients/{scenario.other_recipient_id}/care-entries"
    client.cookies.clear()
    assert as_user(client, "cuidador@test.example").post(other_recipient, json={"category": "food", "text": "x"}).status_code == 404
    client.cookies.clear()
    family = as_user(client, "familia@test.example", family=True)
    assert family.get(_entries(scenario)).status_code in {401, 403, 404}


def test_tasks_flow_complete_and_cancel_rules(client: TestClient, scenario: Scenario) -> None:
    tasks = f"/api/care-units/{scenario.unit_id}/care-tasks"
    caregiver = as_user(client, "cuidador@test.example")
    first = caregiver.post(tasks, json={"title": "Llamar a la hija", "care_recipient_id": scenario.recipient_id}).json()
    second = caregiver.post(tasks, json={"title": "Reponer pañales", "due_on": "2026-11-01"}).json()
    assert [t["title"] for t in caregiver.get(tasks).json()] == ["Reponer pañales", "Llamar a la hija"]
    assert caregiver.post(tasks, json={"title": "x", "care_recipient_id": scenario.other_recipient_id}).status_code == 404

    client.cookies.clear()
    other = as_user(client, "bandeja@test.example")
    assert other.post(f"{tasks}/{second['id']}/cancel", json={}).status_code == 403
    done = other.post(f"{tasks}/{first['id']}/complete", json={"note": "Avisada"})
    assert done.status_code == 200 and done.json()["status"] == "done" and done.json()["closed_by_name"] == "Bandeja"
    assert other.post(f"{tasks}/{first['id']}/complete", json={}).status_code == 409
    assert [t["title"] for t in other.get(tasks).json()] == ["Reponer pañales"]
    assert [t["title"] for t in other.get(f"{tasks}?status=closed").json()] == ["Llamar a la hija"]
    handover = other.get(f"/api/care-units/{scenario.unit_id}/handover").json()
    assert [t["title"] for t in handover["open_tasks"]] == ["Reponer pañales"]
