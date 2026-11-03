"""Fotos en novedades: consentimiento de imagen, confirmación y visibilidad."""

import base64
import copy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from momento_api.care_settings import DEFAULTS
from tests.access_helpers import Scenario, as_user, client, scenario  # noqa: F401

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PHOTO = {"content_type": "image/png", "data": base64.b64encode(PNG).decode()}


@pytest.fixture(autouse=True)
def documents_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("MOMENTO_DOCUMENTS_DIR", str(tmp_path))
    return tmp_path


def _base(s: Scenario) -> str:
    return f"/api/care-units/{s.unit_id}/care-recipients/{s.recipient_id}"


def _grant(client: TestClient, s: Scenario) -> None:
    as_user(client, "jefa@test.example").post(
        f"/api/organizations/{s.organization_id}/family-authorizations",
        json={"family_membership_id": s.memberships["family"], "care_recipient_id": s.recipient_id, "categories": ["updates"]},
    )


def _consent(client: TestClient, s: Scenario, email: str = "medica@test.example"):
    return as_user(client, email).put(f"{_base(s)}/image-consent", json={"given_by": "La persona, por escrito", "given_on": "2026-10-01"})


def test_photo_needs_consent_and_confirmation(client: TestClient, scenario: Scenario) -> None:
    _grant(client, scenario)
    caregiver = as_user(client, "cuidador@test.example")
    assert caregiver.post(f"{_base(scenario)}/family-updates", json={"text": "Taller", "photo": PHOTO, "others_confirmed": True}).status_code == 409
    assert _consent(client, scenario, "cuidador@test.example").status_code == 403
    assert _consent(client, scenario).status_code == 200
    caregiver = as_user(client, "cuidador@test.example")
    assert caregiver.get(f"{_base(scenario)}/family-updates").json()["image_consent"]["given_by"] == "La persona, por escrito"
    assert caregiver.post(f"{_base(scenario)}/family-updates", json={"text": "Taller", "photo": PHOTO}).status_code == 422
    fake = {"content_type": "image/png", "data": base64.b64encode(b"%PDF-1.4").decode()}
    assert caregiver.post(f"{_base(scenario)}/family-updates", json={"text": "x", "photo": fake, "others_confirmed": True}).status_code == 415
    created = caregiver.post(f"{_base(scenario)}/family-updates", json={"text": "Taller", "photo": PHOTO, "others_confirmed": True})
    assert created.status_code == 201 and created.json()["has_photo"] is True
    staff_photo = caregiver.get(f"/api/care-units/{scenario.unit_id}/family-updates/{created.json()['id']}/photo")
    assert staff_photo.status_code == 200 and staff_photo.content == PNG

    family = as_user(client, "familia@test.example", family=True)
    item = family.get("/api/family/updates").json()[0]
    assert item["has_photo"] is True
    photo = family.get(f"/api/family/updates/{item['id']}/photo")
    assert photo.status_code == 200 and photo.content == PNG and photo.headers["cache-control"] == "private, no-store"


def test_revoking_consent_or_disabling_photos_hides_them(client: TestClient, scenario: Scenario) -> None:
    _grant(client, scenario)
    _consent(client, scenario)
    update = as_user(client, "cuidador@test.example").post(
        f"{_base(scenario)}/family-updates", json={"text": "Paseo", "photo": PHOTO, "others_confirmed": True}).json()
    assert as_user(client, "jefa@test.example").delete(f"{_base(scenario)}/image-consent").status_code == 204
    family = as_user(client, "familia@test.example", family=True)
    item = family.get("/api/family/updates").json()[0]
    assert item["text"] == "Paseo" and item["has_photo"] is False
    assert family.get(f"/api/family/updates/{update['id']}/photo").status_code == 404

    _consent(client, scenario)
    settings = copy.deepcopy(DEFAULTS)
    settings["family_update_photos"] = False
    as_user(client, "jefa@test.example").put(
        f"/api/organizations/{scenario.organization_id}/care-units/{scenario.unit_id}/care-settings", json=settings)
    family = as_user(client, "familia@test.example", family=True)
    assert family.get(f"/api/family/updates/{update['id']}/photo").status_code == 404
    caregiver = as_user(client, "cuidador@test.example")
    assert caregiver.post(f"{_base(scenario)}/family-updates", json={"text": "x", "photo": PHOTO, "others_confirmed": True}).status_code == 422


def test_photo_not_reachable_by_other_unit_or_after_withdraw(client: TestClient, scenario: Scenario) -> None:
    _grant(client, scenario)
    _consent(client, scenario)
    update = as_user(client, "cuidador@test.example").post(
        f"{_base(scenario)}/family-updates", json={"text": "Foto", "photo": PHOTO, "others_confirmed": True}).json()
    south = as_user(client, "medicosur@test.example")
    assert south.get(f"/api/care-units/{scenario.unit_id}/family-updates/{update['id']}/photo").status_code == 404
    assert south.get(f"/api/care-units/{scenario.other_unit_id}/family-updates/{update['id']}/photo").status_code == 404
    as_user(client, "cuidador@test.example").post(
        f"/api/care-units/{scenario.unit_id}/family-updates/{update['id']}/withdraw", json={"reason": "Error"})
    family = as_user(client, "familia@test.example", family=True)
    assert family.get(f"/api/family/updates/{update['id']}/photo").status_code == 404
