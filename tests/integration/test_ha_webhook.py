import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

# Mock HA Secret
settings.HA_WEBHOOK_SECRET = "test_secret"


@pytest.mark.asyncio
async def test_ha_webhook_auth_failure():
    # No Token - FastAPI raises 422 for missing required header
    response = client.post("/api/nerves/perceive", json={"trigger": "test"})
    assert response.status_code == 422

    # Wrong Token
    response = client.post("/api/nerves/perceive", json={"trigger": "test"}, headers={"X-LifeGame-Token": "wrong"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ha_webhook_success():
    from unittest.mock import patch, MagicMock, AsyncMock
    from domain.models.game_result import GameResult

    # Mock PerceptionService
    with patch(
        "application.services.perception_service.perception_service.process_event", new_callable=AsyncMock
    ) as mock_process:
        # Setup Mock
        mock_result = GameResult(text="Mock Narrative", metadata={"actions_taken": ["mock_action"]})
        mock_process.return_value = mock_result

        payload = {"event_type": "screen_on", "entity_id": "phone_1", "user_id": "test_user"}

        response = client.post("/api/nerves/perceive", json=payload, headers={"X-LifeGame-Token": "test_secret"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["narrative"] == "Mock Narrative"
        assert data["impact"] == "neutral"  # screen_on has neutral impact

        # Verify PerceptionService was called
        mock_process.assert_called_once()
