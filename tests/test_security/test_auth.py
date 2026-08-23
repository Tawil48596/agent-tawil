from fastapi import FastAPI
from fastapi.testclient import TestClient

from plugins.web_ui.api.auth import APIKeyManager, AuthenticationMiddleware, router


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(AuthenticationMiddleware)
    app.include_router(router)

    @app.get("/api/v1/private")
    async def private_route():
        return {"ok": True}

    return TestClient(app)


def test_login_rejects_invalid_credentials(monkeypatch):
    monkeypatch.setenv("AGENT_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("AGENT_ADMIN_PASSWORD", "correct-horse-battery-staple")

    response = _client().post(
        "/api/v1/auth/token",
        json={"username": "admin", "password": "wrong"},
    )

    assert response.status_code == 401


def test_protected_api_accepts_issued_token(monkeypatch):
    monkeypatch.setenv("AGENT_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("AGENT_ADMIN_PASSWORD", "correct-horse-battery-staple")
    client = _client()

    assert client.get("/api/v1/private").status_code == 401
    login = client.post(
        "/api/v1/auth/token",
        json={"username": "admin", "password": "correct-horse-battery-staple"},
    )
    token = login.json()["access_token"]

    response = client.get(
        "/api/v1/private",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_api_key_creation_requires_existing_identity(monkeypatch):
    monkeypatch.setenv("AGENT_ADMIN_PASSWORD", "correct-horse-battery-staple")
    client = _client()
    login = client.post(
        "/api/v1/auth/token",
        json={"username": "admin", "password": "correct-horse-battery-staple"},
    )
    token = login.json()["access_token"]

    denied = client.post("/api/v1/auth/api-key")
    allowed = client.post(
        "/api/v1/auth/api-key?name=automation",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert denied.status_code == 401
    assert allowed.status_code == 200
    assert allowed.json()["api_key"].startswith("sk-")


def test_api_key_digests_are_keyed_per_manager():
    """The same credential must not have a reusable, global digest."""
    first = APIKeyManager()
    second = APIKeyManager()

    assert first._hash("sk-fixed-regression-value") != second._hash(
        "sk-fixed-regression-value"
    )
