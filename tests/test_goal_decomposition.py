import pytest
from unittest.mock import AsyncMock, patch
from app.services.quest_service import quest_service
from app.models.quest import Quest
from app.models.dda import HabitState


@pytest.mark.asyncio
async def test_create_new_goal_decomposition():
    # Mock Session
    mock_session = AsyncMock()

    # Mock AI Response
    ai_response = {
        "milestones": [{"title": "閱讀第一章", "desc": "開始閱讀", "difficulty": "C"}],
        "daily_habits": [{"title": "每天閱讀 10 分鐘", "desc": "每日固定時段"}],
    }

    with patch(
        "app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = ai_response

        # Execute
        goal, plan = await quest_service.create_new_goal(
            mock_session, "u1", "Learn Python"
        )

        assert goal.title == "Learn Python"

        # Verify Session Adds
        # We expect: 1 Goal, 1 Quest (Milestone), 1 HabitState
        assert mock_session.add.call_count >= 3

        # Inspect calls to ensure correct types
        added_objects = [call[0][0] for call in mock_session.add.call_args_list]

        has_quest = any(
            isinstance(obj, Quest) and obj.title == "閱讀第一章"
            for obj in added_objects
        )
        has_habit = any(
            isinstance(obj, HabitState) and obj.habit_name == "每天閱讀 10 分鐘"
            for obj in added_objects
        )

        assert has_quest
        assert has_habit
