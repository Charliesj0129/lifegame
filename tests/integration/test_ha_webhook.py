import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

# Mock HA Secret
settings.HA_WEBHOOK_SECRET = "test_secret"

@pytest.mark.asyncio
async def test_ha_webhook_auth_failure():
    # No Token
    response = client.post("/api/nerves/perceive", json={"trigger": "test"})
    assert response.status_code == 401
    
    # Wrong Token
    response = client.post("/api/nerves/perceive", json={"trigger": "test"}, headers={"X-LifeGame-Token": "wrong"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_ha_webhook_success():
    from unittest.mock import patch, MagicMock
    
    # Mock GameLoop
    with patch("application.services.game_loop.game_loop.process_message") as mock_process:
        # Setup Mock
        mock_result = MagicMock()
        mock_result.text = "Mock Narrative"
        mock_result.metadata = {"actions": ["mock_action"]}
        mock_process.return_value = mock_result

        payload = {
            "trigger": "screen_on",
            "entity_id": "phone_1",
            "user_id": "test_user"
        }
        
        response = client.post(
            "/api/nerves/perceive", 
            json=payload, 
            headers={"X-LifeGame-Token": "test_secret"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["narrative"] == "Mock Narrative"
        
        # Verify GameLoop call
        args, _ = mock_process.call_args
        # args[0] is session (Depends), args[1] is user_id, args[2] is text
        assert args[1] == "test_user"
        assert "Home Assistant Event: screen_on" in args[2]
