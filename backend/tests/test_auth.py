from fastapi.testclient import TestClient

from momento_api.auth import hash_password, verify_password


def test_password_hash_uses_scrypt_and_verifies() -> None:
    encoded = hash_password("ClaveFuerteMomento2026!")
    assert encoded.startswith("scrypt$")
    assert verify_password("ClaveFuerteMomento2026!", encoded)
    assert not verify_password("OtraClave2026!", encoded)


def test_login_rejects_invalid_password_with_generic_error(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/auth/login",
        json={"email": "encargada@example.test", "password": "incorrecta"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Correo o contraseña incorrectos."


def test_logout_revokes_session_and_protected_routes_require_login(api_client: TestClient) -> None:
    logout = api_client.post("/api/auth/logout")
    assert logout.status_code == 204
    assert api_client.get("/api/organizations").status_code == 401
