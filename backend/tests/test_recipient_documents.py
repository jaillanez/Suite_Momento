"""Documentos adjuntos a la ficha: tipos, tamaño, permisos y auditoría."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.access_helpers import Scenario, as_user, client, scenario  # noqa: F401

PDF = b"%PDF-1.4\n%ficticio\n"


@pytest.fixture(autouse=True)
def documents_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("MOMENTO_DOCUMENTS_DIR", str(tmp_path))
    return tmp_path


def _docs(s: Scenario) -> str:
    return f"/api/care-units/{s.unit_id}/care-recipients/{s.recipient_id}/documents"


def _upload(client: TestClient, s: Scenario, content: bytes = PDF, content_type: str = "application/pdf", filename: str = "dni.pdf"):
    return client.post(
        _docs(s),
        params={"title": "DNI", "category": "identity", "filename": filename},
        content=content,
        headers={"Content-Type": content_type},
    )


def test_manager_uploads_staff_downloads_and_it_is_audited(
    client: TestClient, scenario: Scenario, documents_dir: Path
) -> None:
    as_user(client, "jefa@test.example")
    uploaded = _upload(client, scenario, filename="../../etc/DNI \"Elena\".pdf")
    assert uploaded.status_code == 201, uploaded.text
    document = uploaded.json()
    assert document["original_filename"] == "DNI Elena.pdf"
    stored = list(documents_dir.iterdir())
    assert len(stored) == 1 and stored[0].read_bytes() == PDF
    assert oct(stored[0].stat().st_mode)[-3:] == "600"

    as_user(client, "cuidador@test.example")
    profile = client.get(f"/api/care-units/{scenario.unit_id}/care-recipients/{scenario.recipient_id}").json()
    assert [d["id"] for d in profile["documents"]] == [document["id"]]
    assert profile["can_manage_documents"] is False
    downloaded = client.get(f"{_docs(scenario)}/{document['id']}")
    assert downloaded.status_code == 200
    assert downloaded.content == PDF
    assert downloaded.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in downloaded.headers["content-disposition"]
    assert _upload(client, scenario).status_code == 403
    assert client.delete(f"{_docs(scenario)}/{document['id']}").status_code == 403

    as_user(client, "jefa@test.example")
    actions = {(e["action"], e["outcome"]) for e in client.get(f"/api/organizations/{scenario.organization_id}/audit-events").json()}
    assert ("care_recipient.document_uploaded", "success") in actions
    assert ("care_recipient.document_downloaded", "success") in actions
    assert ("care_recipient.document_uploaded", "denied") in actions

    assert client.delete(f"{_docs(scenario)}/{document['id']}").status_code == 204
    assert list(documents_dir.iterdir()) == []


def test_rejects_wrong_type_spoofed_content_and_empty_files(client: TestClient, scenario: Scenario) -> None:
    as_user(client, "jefa@test.example")
    assert _upload(client, scenario, content=b"MZ\x90", content_type="application/x-msdownload").status_code == 415
    assert _upload(client, scenario, content=b"<html>", content_type="application/pdf").status_code == 415
    assert _upload(client, scenario, content=b"", content_type="application/pdf").status_code == 422
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 10
    assert _upload(client, scenario, content=png, content_type="image/png", filename="foto.png").status_code == 201


def test_rejects_files_over_10_mb(client: TestClient, scenario: Scenario) -> None:
    as_user(client, "jefa@test.example")
    big = PDF + b"0" * (10 * 1024 * 1024)
    assert _upload(client, scenario, content=big).status_code == 413


def test_documents_are_scoped_to_service(client: TestClient, scenario: Scenario) -> None:
    as_user(client, "jefa@test.example")
    document = _upload(client, scenario).json()
    as_user(client, "medicosur@test.example")
    assert client.get(f"{_docs(scenario)}/{document['id']}").status_code == 404
    other = f"/api/care-units/{scenario.other_unit_id}/care-recipients/{scenario.recipient_id}/documents/{document['id']}"
    assert client.get(other).status_code == 404
