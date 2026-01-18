import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from domain.events.game_event import GameEvent
from application.services.perception_service import PerceptionService
from app.schemas.webhook import HAEventPayload
from adapters.perception.ha_adapter import HomeAssistantAdapter


@pytest.fixture
def mock_dependencies():
    with (
        patch("application.services.perception_service.container") as mock_container,
        patch("application.services.perception_service.vector_service") as mock_vector,
        patch("application.services.perception_service.brain_service") as mock_brain,
        patch("application.services.perception_service.action_service") as mock_actions,
    ):
        # Mock Graph (via Container)
        mock_graph_service = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.has_next.side_effect = [True, False]
        mock_cursor.get_next.return_value = ["Viper", "Mentor"]
        # query returns list now, not cursor wrapper?
        # Check graph_service.query -> GraphPort.query. 
        # Refactored graph_service.query returns list via adapter.
        # But old test used cursor wrapper mock.
        # Let's mock query to return a list
        mock_graph_service.query.return_value = [["Viper", "Mentor"]]
        
        mock_container.graph_service = mock_graph_service
        
        # Mock Vector
        mock_vector.search_memories = AsyncMock(return_value=["Memory 1"])

        # Mock Brain
        mock_brain.think = AsyncMock(return_value='{"narrative": "Test Narrative", "actions": []}')

        yield mock_graph_service, mock_vector, mock_brain, mock_actions


@pytest.mark.asyncio
async def test_perception_service_flow(mock_dependencies):
    mock_graph, mock_vector, mock_brain, mock_actions = mock_dependencies

    service = PerceptionService()
    event = GameEvent(source="ha", source_id="test", type="test_event", metadata={})

    result = await service.process_event(event)

    assert result.text == "Test Narrative"
    mock_graph.query.assert_called_once()
    mock_vector.search_memories.assert_called_once()
    mock_brain.think.assert_called_once()


def test_ha_adapter():
    adapter = HomeAssistantAdapter()
    # Use dict directly since adapter supports both Pydantic models and dicts
    payload = {"trigger": "screen_on", "entity_id": "device.phone", "state": "on", "brightness": 100}
    event = adapter.to_game_event(payload)

    assert event.type == "HA_SCREEN_ON"  # Matches actual implementation
    assert event.metadata["state"] == "on"
    assert event.source == "home_assistant"
