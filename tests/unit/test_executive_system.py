import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from application.services.brain_service import BrainService, AgentSystemAction
from legacy.services.quest_service import QuestService
from legacy.models.quest import Quest, QuestStatus
import datetime


@pytest.fixture
def mock_session():
    session = AsyncMock()
    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result
    return session


@pytest.mark.unit
@pytest.mark.asyncio
async def test_executive_judgment_overwhelm(mock_session):
    """
    Test that BrainService detects "Overwhelm" (Stale Quests)
    and triggers DIFFICULTY_CHANGE.
    """
    brain_service = BrainService()
    user_id = "test_user"

    # Mock Active Quests that are OLD (3 days old)
    old_date = datetime.datetime.now() - datetime.timedelta(days=3)
    stale_quests = [
        Quest(id="q1", user_id=user_id, status=QuestStatus.ACTIVE.value, created_at=old_date),
        Quest(id="q2", user_id=user_id, status=QuestStatus.ACTIVE.value, created_at=old_date),
    ]

    # Mock DB Query
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = stale_quests
    mock_session.execute.return_value = mock_result

    # Mock QuestService
    with patch(
        "legacy.services.quest_service.quest_service.bulk_adjust_difficulty", new_callable=AsyncMock
    ) as mock_adjust:
        mock_adjust.return_value = 2  # 2 quests updated

        # Execute
        action = await brain_service.execute_system_judgment(mock_session, user_id)

        # Assert
        assert action is not None
        assert action.action_type == "DIFFICULTY_CHANGE"
        assert action.details["tier"] == "E"
        assert action.details["count"] == 2
        mock_adjust.assert_called_once_with(mock_session, user_id, target_tier="E")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_executive_judgment_normal(mock_session):
    """
    Test that fresh quests DO NOT trigger intervention.
    """
    brain_service = BrainService()
    user_id = "test_user"

    # Mock Active Quests that are NEW (0 days old)
    new_date = datetime.datetime.now()
    fresh_quests = [
        Quest(id="q1", user_id=user_id, status=QuestStatus.ACTIVE.value, created_at=new_date),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = fresh_quests
    mock_session.execute.return_value = mock_result

    with patch(
        "legacy.services.quest_service.quest_service.bulk_adjust_difficulty", new_callable=AsyncMock
    ) as mock_adjust:
        action = await brain_service.execute_system_judgment(mock_session, user_id)
        assert action is None
        mock_adjust.assert_not_called()
