import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.quest import Goal, GoalStatus, Quest, QuestStatus
from application.services.brain_service import AgentSystemAction, BrainService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    # Mock default responses
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = None
    session.execute.return_value = mock_result
    return session


@pytest.mark.unit
@pytest.mark.asyncio
async def test_executive_bridge_stagnation(mock_session):
    """
    Test that BrainService detects "Stagnation" (Goal with no recent quests)
    and triggers BRIDGE_GEN.
    """
    brain_service = BrainService()
    user_id = "test_user"
    now = datetime.datetime.now()

    # 1. Mock No Active Quests (So it falls through to Step 4)
    # The first execute call is active_quests -> []

    # 2. Mock Active Goal (Old)
    old_date = now - datetime.timedelta(days=10)
    stagnant_goal = Goal(
        id="g1", user_id=user_id, title="Learn Rust", status=GoalStatus.ACTIVE.value, created_at=old_date
    )

    # We need to structure the side effects of session.execute
    # Call 1: Active Quests -> []
    # Call 2: Active Goals -> [stagnant_goal]
    # Call 3: Last Quest for Goal -> None (None found)

    # Mock Setup
    mock_active_quests = MagicMock()
    mock_active_quests.scalars.return_value.all.return_value = []

    mock_active_goals = MagicMock()
    mock_active_goals.scalars.return_value.all.return_value = [stagnant_goal]

    mock_last_quest = MagicMock()
    mock_last_quest.scalars.return_value.first.return_value = None

    mock_session.execute.side_effect = [mock_active_quests, mock_active_goals, mock_last_quest]

    # Mock QuestService
    with patch(
        "application.services.quest_service.quest_service.create_bridge_quest", new_callable=AsyncMock
    ) as mock_bridge:
        mock_bridge.return_value = Quest(title="Install Rust", goal_id="g1")

        # Execute
        action = await brain_service.execute_system_judgment(mock_session, user_id)

        # Assert
        assert action is not None
        assert action.action_type == "BRIDGE_GEN"
        assert action.details["goal"] == "Learn Rust"
        mock_bridge.assert_called_once_with(mock_session, user_id, "g1")
