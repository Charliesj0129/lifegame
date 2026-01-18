import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.api.line_webhook import webhook_handler
from sqlalchemy import select
from app.models.user import User

# -----------------------------------------------------------------------------
# System Test Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def client():
    # Use TestClient with the global app
    return TestClient(app)

@pytest.fixture
def mock_line_signature():
    """Bypass LINE Signature Validation for tests"""
    # We patch the validator inside the handler.parser
    # Note: webhook_handler is a global object in app.api.line_webhook
    if not webhook_handler:
        yield None
        return
        
    original = webhook_handler.parser.signature_validator.validate
    webhook_handler.parser.signature_validator.validate = MagicMock(return_value=True)
    yield
    webhook_handler.parser.signature_validator.validate = original

@pytest.fixture
def mock_line_client():
    """Mock the output client to verify replies"""
    with patch("adapters.perception.line_client.line_client.send_reply", new_callable=AsyncMock) as mock_reply:
         with patch("adapters.perception.line_client.line_client.send_push", new_callable=AsyncMock) as mock_push:
            yield {"reply": mock_reply, "push": mock_push}

# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data

@pytest.mark.asyncio
async def test_webhook_status_command(client, mock_line_signature, mock_line_client, db_session):
    """
    E2E: User sends '狀態' -> Webhook -> Dispatcher -> Status Handler -> Reply
    Note: TestClient is synchronous, but the app spawns background tasks.
    We need to ensure background tasks run. TestClient usually runs them if using BackgroundTasks.
    """
    
    # Payload for a Text Message "狀態"
    user_id = "e2e_user_status"
    payload = {
        "destination": "U1234567890",
        "events": [
            {
                "type": "message",
                "message": {"type": "text", "id": "123456", "text": "狀態", "quoteToken": "q_token_123"},
                "webhookEventId": "01FZ74A0TDDPYRVKNK77XKC3ZR",
                "deliveryContext": {"isRedelivery": False},
                "timestamp": 1618721953123,
                "source": {"type": "user", "userId": user_id},
                "replyToken": "test_reply_token",
                "mode": "active"
            }
        ]
    }
    
    # 1. Send Request
    # TestClient runs in same loop? FastApi BackgroundTasks run after response.
    # In synchronous TestClient, it waits for response.
    # But Background Tasks are executed *after* response is sent.
    # Starlette TestClient (used by FastAPI) executes background tasks automatically ?
    # Yes, usually unless explicitly disabled.
    
    # HOWEVER, our `process_webhook_background` is an async function added to tasks.
    # We need to make sure db_session used in test matches or we rely on the app's internal session creation.
    # The app creates its own `AsyncSessionLocal`. In System tests using TestClient, 
    # the app usually uses its configured DB.
    # In `conftest.py`, we override `AsyncSessionLocal`? Not for system tests usually, unless we want to spy on DB.
    # Let's hope the environment uses the test DB or we patch `AsyncSessionLocal`.
    
    # Patch AsyncSessionLocal to use our passed-in db_session? 
    # It's hard because `AsyncSessionLocal` is a class/maker.
    # Easier to verify via Mock Side Effects or just trust the mocked Line Client.
    
    # Let's clean headers
    headers = {"X-Line-Signature": "dummy_sig"}
    
    # To enable "Background Task" execution in pytest-asyncio context for FastAPI...
    # Actually, verify if TestClient executes them. It does.
    
    with patch("app.core.database.AsyncSessionLocal") as mock_session_cls:
        # Mock the session factory to return our test db_session
        # This requires the test db_session to be async-compatible in this context
        mock_session_cls.return_value.__aenter__.return_value = db_session
        
        response = client.post("/line/callback", json=payload, headers=headers)
        
        assert response.status_code == 200
        assert response.json() == {"status": "accepted", "mode": "async_processing"}
        
    # Wait/Check for side effects
    # Since background tasks are run, valid reply should have notably called `send_reply`
    
    # Assert
    mock_line_client["reply"].assert_called()
    call_args = mock_line_client["reply"].call_args
    assert call_args is not None
    token, result = call_args[0]
    assert token == "test_reply_token"
    # assert "玩家狀態" in result.text # 'result' is GameResult object

@pytest.mark.asyncio
async def test_webhook_checkin_flow(client, mock_line_signature, mock_line_client, db_session):
    """
    E2E: User sends '簽到' -> ... -> DB Update (+Gold) -> Reply
    """
    user_id = "e2e_user_checkin"
    
    # Pre-create user to verify delta
    user = User(id=user_id, name="Checkin User", gold=100, xp=0)
    db_session.add(user)
    await db_session.commit()
    
    payload = {
        "destination": "U1234567890",
        "events": [
            {
                "type": "message",
                "message": {"type": "text", "id": "123456", "text": "簽到", "quoteToken": "q_token_456"},
                "timestamp": 1618721953123,
                "webhookEventId": "01FZ74A0TDDPYRVKNK77XKC3ZR",
                "deliveryContext": {"isRedelivery": False},
                "source": {"type": "user", "userId": user_id},
                "replyToken": "token_checkin",
                "mode": "active"
            }
        ]
    }
    
    headers = {"X-Line-Signature": "dummy_sig"}
    
    # Patch DB Session
    with patch("app.core.database.AsyncSessionLocal") as mock_session_cls:
        mock_session_cls.return_value.__aenter__.return_value = db_session
        
        response = client.post("/line/callback", json=payload, headers=headers)
        assert response.status_code == 200

    # Verify Logic
    mock_line_client["reply"].assert_called()
    
    # Verify DB Persistence
    # Note: Because we shared the session, we needs to refresh (or query)
    await db_session.refresh(user)
    assert user.gold == 110 # Started 100 + 10 checkin
    assert user.xp == 5

