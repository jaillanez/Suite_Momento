"""Novedades para la familia: solo lo que el equipo publica, solo a quien tiene permiso."""

import copy

from fastapi.testclient import TestClient

from momento_api.care_settings import DEFAULTS
from tests.access_helpers import Scenario, as_user, client, scenario  # noqa: F401


def _updates(s: Scenario, recipient: str | None = None) -> str:
    return f"/api/care-units/{s.unit_id}/care-recipients/{recipient or s.recipient_id}/family-updates"


def _grant(client: TestClient, s: Scenario, categories=("updates",)) -> list[dict]:
    as_user(client, "jefa@test.example")
    response = client.post(
        f"/api/organizations/{s.organization_id}/family-authorizations",
        json={"family_membership_id": s.memberships["family"], "care_recipient_id": s.recipient_id, "categories": list(categories)},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_nothing_reaches_family_without_publishing(client: TestClient, scenario: Scenario) -> None:
    _grant(client, scenario)
    caregiver = as_user(client, "cuidador@test.example")
    caregiver.post(f"/api/care-units/{scenario.unit_id}/care-recipients/{scenario.recipient_id}/care-entries",
                   json={"category": "health", "text": "Tos seca"})
    family = as_user(client, "familia@test.example", family=True)
    assert family.get("/api/family/updates").json() == []


def test_publish_from_entry_reaches_authorized_family_with_notice(client: TestClient, scenario: Scenario) -> None:
    _grant(client, scenario)
    caregiver = as_user(client, "cuidador@test.example")
    entry = caregiver.post(f"/api/care-units/{scenario.unit_id}/care-recipients/{scenario.recipient_id}/care-entries",
                           json={"category": "activity", "text": "Taller de jardinería"}).json()
    listing = caregiver.get(_updates(scenario)).json()
    assert listing["can_publish"] is True and listing["readers"] == ["Familia"]
    published = caregiver.post(_updates(scenario), json={"text": "Hoy disfrutó del taller de jardinería.", "source_entry_id": entry["id"]})
    assert published.status_code == 201, published.text
    assert published.json()["from_entry"] is True

    family = as_user(client, "familia@test.example", family=True)
    items = family.get("/api/family/updates").json()
    assert [i["text"] for i in items] == ["Hoy disfrutó del taller de jardinería."]
    assert items[0]["published_by_role"] == "Cuidador/a" and "published_by_name" not in items[0]
    notices = family.get("/api/family/notifications").json()
    assert notices["unread"] == 1 and notices["items"][0]["kind"] == "family_update"
    assert family.post(f"/api/family/notifications/{notices['items'][0]['id']}/read").status_code == 204
    # El personal no recibe el aviso familiar ni la familia entra a los avisos del personal.
    assert family.get("/api/notifications").status_code in {401, 403, 404}


def test_family_without_updates_permission_sees_nothing(client: TestClient, scenario: Scenario) -> None:
    _grant(client, scenario, ("medication", "diet"))
    caregiver = as_user(client, "cuidador@test.example")
    blocked = caregiver.post(_updates(scenario), json={"text": "Algo"})
    assert blocked.status_code == 409  # nadie podría leerla
    family = as_user(client, "familia@test.example", family=True)
    assert family.get("/api/family/updates").json() == []


def test_revoking_permission_hides_updates_and_notices(client: TestClient, scenario: Scenario) -> None:
    granted = _grant(client, scenario)
    as_user(client, "cuidador@test.example").post(_updates(scenario), json={"text": "Buen día"})
    manager = as_user(client, "jefa@test.example")
    assert manager.post(f"/api/organizations/{scenario.organization_id}/family-authorizations/{granted[0]['id']}/revoke").status_code == 200
    family = as_user(client, "familia@test.example", family=True)
    assert family.get("/api/family/updates").json() == []
    assert family.get("/api/family/notifications").json() == {"unread": 0, "items": []}


def test_withdraw_rules(client: TestClient, scenario: Scenario) -> None:
    _grant(client, scenario)
    update = as_user(client, "cuidador@test.example").post(_updates(scenario), json={"text": "Paseo por el jardín"}).json()
    withdraw = f"/api/care-units/{scenario.unit_id}/family-updates/{update['id']}/withdraw"
    other = as_user(client, "bandeja@test.example")
    assert other.post(withdraw, json={"reason": "No corresponde"}).status_code == 403
    author = as_user(client, "cuidador@test.example")
    done = author.post(withdraw, json={"reason": "Era otra persona"})
    assert done.status_code == 200 and done.json()["withdrawn"] is True
    assert author.post(withdraw, json={"reason": "otra vez"}).status_code == 409
    family = as_user(client, "familia@test.example", family=True)
    assert family.get("/api/family/updates").json() == []
    assert family.get("/api/family/notifications").json()["items"] == []


def test_publishing_roles_follow_settings(client: TestClient, scenario: Scenario) -> None:
    _grant(client, scenario)
    settings = copy.deepcopy(DEFAULTS)
    settings.update(family_update_roles=["manager"], family_update_notify=False)
    manager = as_user(client, "jefa@test.example")
    put = f"/api/organizations/{scenario.organization_id}/care-units/{scenario.unit_id}/care-settings"
    assert manager.put(put, json=settings).status_code == 200
    caregiver = as_user(client, "cuidador@test.example")
    assert caregiver.get(_updates(scenario)).json()["can_publish"] is False
    assert caregiver.post(_updates(scenario), json={"text": "x"}).status_code == 403
    handover = caregiver.get(f"/api/care-units/{scenario.unit_id}/handover").json()
    assert handover["settings"]["can_share_with_family"] is False
    manager = as_user(client, "jefa@test.example")
    assert manager.post(_updates(scenario), json={"text": "Visita del médico sin novedades."}).status_code == 201
    family = as_user(client, "familia@test.example", family=True)
    assert len(family.get("/api/family/updates").json()) == 1
    assert family.get("/api/family/notifications").json()["unread"] == 0  # aviso desactivado


def test_other_unit_and_foreign_entry_rejected(client: TestClient, scenario: Scenario) -> None:
    _grant(client, scenario)
    south = as_user(client, "medicosur@test.example")
    assert south.get(_updates(scenario)).status_code == 404
    assert south.post(_updates(scenario), json={"text": "x"}).status_code == 404
    # Un registro de otra persona no sirve como origen.
    manager = as_user(client, "jefa@test.example")
    other_entry = manager.post(
        f"/api/care-units/{scenario.other_unit_id}/care-recipients/{scenario.other_recipient_id}/care-entries",
        json={"category": "food", "text": "Almorzó"},
    ).json()
    assert manager.post(_updates(scenario), json={"text": "x", "source_entry_id": other_entry["id"]}).status_code == 404
