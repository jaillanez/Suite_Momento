from fastapi.testclient import TestClient

import momento_api.main as main

client = TestClient(main.app)


def test_api_health_reports_ok() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "momento-api"}


def test_database_health_hides_connection_details(monkeypatch) -> None:
    monkeypatch.setattr(main, "database_is_ready", lambda: False)

    response = client.get("/api/health/database")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "PostgreSQL no está configurado o no responde."
    }
