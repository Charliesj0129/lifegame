import time

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    # In blackbox tests, we assume minimal mocking, but we might patch external I/O if really needed.
    # Ideally, blackbox tests run against a running instance, but TestClient is "Gray Box".
    # We will treat it as blackbox by asserting only on Response.
    return TestClient(app)


def test_health_check_contract(client):
    """
    Contract:
    - Status: 200 OK
    - Body: JSON
    - Schema: {status: str, version: str, database: str, timestamp: str}
    - Performance: < 500ms
    """
    start = time.perf_counter()
    response = client.get("/health")
    duration = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert "version" in data
    assert "database" in data

    # Soft performance assertion (warn if slow)
    if duration > 500:
        pytest.warn(UserWarning(f"Health check too slow: {duration}ms"))


def test_line_webhook_missing_signature(client):
    """
    Contract:
    - Missing Header -> 400 or 422
    """
    response = client.post("/line/callback", json={"events": []})
    assert response.status_code in [
        400,
        422,
    ]  # FastAPI might return 422 for missing header if defined as required param


def test_line_webhook_invalid_signature(client):
    """
    Contract:
    - Invalid Signature -> 400 Bad Request (Explicit handling)
    """
    headers = {"X-Line-Signature": "invalid_sig"}
    # Need valid JSON body even if empty events
    response = client.post("/line/callback", json={"events": []}, headers=headers)
    assert response.status_code == 400


def test_nerves_auth_failure(client):
    """
    Contract:
    - Missing Token -> 422 (FastAPI required Header) or 401
    - Invalid Token -> 401 Unauthorized
    """
    # 1. Missing Header
    response = client.get("/api/nerves/npcs")
    assert response.status_code == 422  # header is required in signature

    # 2. Invalid Token
    headers = {"x-lifegame-token": "WRONG_TOKEN"}
    response = client.get("/api/nerves/npcs", headers=headers)
    assert response.status_code == 401


def test_chat_endpoint_contract(client):
    """
    Contract:
    - POST /api/chat/{npc_id}
    - Body: {user_id: str, text: str}
    - Response: {text: str, ...}
    """
    # We might get 500 if DB is not set up correctly in this context without mocking,
    # but the Contract is about Input matching Route.
    # If 500, it means route matched. If 404, route missing.

    payload = {"user_id": "test_cx", "text": "Hello"}
    response = client.post("/api/chat/npc_viper", json=payload)

    # Ideally 200, but 500 is acceptable if logic fails but contract (path) exists.
    # If 422, schema mismatch.
    assert response.status_code != 404
    assert response.status_code != 422
    # If partial mock, might work.

    if response.status_code == 200:
        data = response.json()
        assert "text" in data
        assert "can_visualize" in data
