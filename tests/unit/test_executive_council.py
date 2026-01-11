
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from application.services.brain_service import BrainService, AgentSystemAction
from legacy.models.quest import Quest, QuestStatus, Goal, GoalStatus
import datetime

@pytest.fixture
def mock_session():
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = None
    session.execute.return_value = mock_result
    return session

@pytest.mark.unit
@pytest.mark.asyncio
async def test_checkmate_protocol(mock_session):
    """
    Test that > 30 days stagnation triggers CHECKMATE (Redemption Quest).
    """
    brain_service = BrainService()
    user_id = "test_user"
    now = datetime.datetime.now()

    # 1. Mock Active Goal (Very Old)
    old_date = now - datetime.timedelta(days=40)
    goal = Goal(id="g1", user_id=user_id, title="Ignored Goal", status=GoalStatus.ACTIVE.value, created_at=old_date)

    mock_goals = MagicMock()
    mock_goals.scalars.return_value.all.return_value = [goal]

    # Side effects: [Active Quests=[], Active Goals=[goal], Last Quest=None]
    mock_session.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        mock_goals,
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None))))
    ]

    action = await brain_service.execute_system_judgment(mock_session, user_id)

    assert action is not None
    assert action.action_type == "PUSH_QUEST"
    assert "CHECKMATE" in action.reason
    assert action.details["type"] == "REDEMPTION"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_reality_sync_overload(mock_session):
    """
    Test that High External Load (>0.8) triggers DIFFICULTY_CHANGE without goal issues.
    """
    brain_service = BrainService()
    user_id = "test_user"

    # Mock clean state (No quests, No goals)
    mock_session.execute.return_value.scalars.return_value.all.return_value = []
    
    # Mock _get_external_load private method to return 0.9
    with patch.object(brain_service, "_get_external_load", new_callable=AsyncMock) as mock_load:
        mock_load.return_value = 0.9
        
        with patch("legacy.services.quest_service.quest_service.bulk_adjust_difficulty", new_callable=AsyncMock) as mock_adjust:
            mock_adjust.return_value = 5
            
            action = await brain_service.execute_system_judgment(mock_session, user_id)
            
            assert action is not None
            assert action.action_type == "DIFFICULTY_CHANGE"
            assert action.reason == "High External Load"
            mock_adjust.assert_called_once_with(mock_session, user_id, target_tier="E")
