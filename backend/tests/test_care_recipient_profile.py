"""Fase 3: ficha completa, contactos y permisos por puesto."""

from fastapi.testclient import TestClient

from tests.access_helpers import Scenario, as_user, client, scenario  # noqa: F401


def _path(s: Scenario) -> str:
    return f"/api/care-units/{s.unit_id}/care-recipients/{s.recipient_id}"


def test_administrative_edits_identity_but_not_health(client: TestClient, scenario: Scenario) -> None:
    as_user(client, "jefa@test.example")
    path = _path(scenario)
    # El administrativo de prueba se crea cambiando el puesto del cuidador.
    client.patch(
        f"/api/organizations/{scenario.organization_id}/memberships/{scenario.memberships['caregiver']}",
        json={"staff_role": "administrative"},
    )
    as_user(client, "cuidador@test.example")
    updated = client.patch(path, json={
        "first_name": " Elena ",
        "birth_date": "1941-03-12",
        "document_type": "DNI",
        "document_number": "4.123.456",
        "room": "12B",
        "health_coverage": "Cobertura Demo",
        "life_history": "Maestra rural durante 30 años.",
    })
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["first_name"] == "Elena"
    assert body["room"] == "12B"
    assert body["can_edit"] is True and body["can_edit_health"] is False
    assert client.patch(path, json={"allergies": "Penicilina"}).status_code == 403
    assert client.patch(path, json={"is_active": False}).status_code == 403


def test_physician_edits_health_and_caregiver_only_reads(client: TestClient, scenario: Scenario) -> None:
    path = _path(scenario)
    as_user(client, "medica@test.example")
    health = client.patch(path, json={"allergies": "Penicilina (dato ficticio)", "diet_notes": "Sin sal"})
    assert health.status_code == 200
    assert health.json()["can_edit_health"] is True

    as_user(client, "cuidador@test.example")
    read = client.get(path)
    assert read.status_code == 200
    assert read.json()["allergies"] == "Penicilina (dato ficticio)"
    assert read.json()["can_edit"] is False
    assert client.patch(path, json={"preferences": "Tango"}).status_code == 403
    assert client.post(f"/api/care-units/{scenario.unit_id}/care-recipients", json={"display_name": "X"}).status_code == 403


def test_profile_validates_dates_and_names(client: TestClient, scenario: Scenario) -> None:
    as_user(client, "jefa@test.example")
    path = _path(scenario)
    assert client.patch(path, json={"birth_date": "2999-01-01"}).status_code == 422
    assert client.patch(path, json={"display_name": "   "}).status_code == 422
    assert client.patch(path, json={"document_type": "Libreta"}).status_code == 422
    cleared = client.patch(path, json={"room": "3", "address": ""})
    assert cleared.json()["address"] is None


def test_profile_is_scoped_to_service(client: TestClient, scenario: Scenario) -> None:
    as_user(client, "medicosur@test.example")
    assert client.get(_path(scenario)).status_code == 404
    as_user(client, "jefa@test.example")
    other_unit = f"/api/care-units/{scenario.other_unit_id}/care-recipients/{scenario.recipient_id}"
    assert client.get(other_unit).status_code == 404


def test_contacts_crud_and_audit(client: TestClient, scenario: Scenario) -> None:
    as_user(client, "jefa@test.example")
    contacts = f"{_path(scenario)}/contacts"
    assert client.post(contacts, json={"full_name": "Sin teléfono", "is_emergency": True}).status_code == 422
    created = client.post(contacts, json={
        "full_name": "Lucía Ferreyra",
        "relationship_label": "Hija",
        "phone": "11 5555-0101",
        "is_emergency": True,
    })
    assert created.status_code == 201
    contact_id = created.json()["id"]
    edited = client.put(f"{contacts}/{contact_id}", json={
        "full_name": "Lucía Ferreyra",
        "relationship_label": "Hija",
        "phone": "11 5555-0101",
        "is_emergency": True,
        "is_legal_representative": True,
    })
    assert edited.json()["is_legal_representative"] is True
    assert client.get(_path(scenario)).json()["contacts"][0]["full_name"] == "Lucía Ferreyra"

    as_user(client, "cuidador@test.example")
    assert client.delete(f"{contacts}/{contact_id}").status_code == 403

    as_user(client, "jefa@test.example")
    assert client.delete(f"{contacts}/{contact_id}").status_code == 204
    events = client.get(f"/api/organizations/{scenario.organization_id}/audit-events").json()
    actions = {(e["action"], e["outcome"]) for e in events}
    assert ("care_recipient.viewed", "success") in actions
    assert ("care_recipient.contacts_changed", "success") in actions
    assert ("care_recipient.contacts_changed", "denied") in actions


def test_manager_deactivates_person(client: TestClient, scenario: Scenario) -> None:
    as_user(client, "jefa@test.example")
    assert client.patch(_path(scenario), json={"is_active": False}).json()["is_active"] is False
    listed = client.get(f"/api/care-units/{scenario.unit_id}/care-recipients").json()
    assert scenario.recipient_id not in [item["id"] for item in listed]
