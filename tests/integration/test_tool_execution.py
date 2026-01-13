import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import handle_ai_analysis
from application.services.brain_service import AgentPlan


@pytest.mark.asyncio
async def test_deep_integration_create_goal():
    """
    Verify that if Brain returns 'create_goal' tool call,
    handle_ai_analysis actually calls quest_service.create_goal.
    """
    mock_session = AsyncMock()
    user_id = "test_user_tool"

    # Mock Brain Service Response
    mock_plan = AgentPlan(
        narrative="Creating goal now.",
        tool_calls=[{"tool": "create_goal", "args": {"title": "Become Strong", "category": "health"}}],
    )

    with patch(
        "application.services.brain_service.brain_service.think_with_session", new_callable=AsyncMock
    ) as mock_think:
        mock_think.return_value = mock_plan

        # Mock Dependencies (User, HP, etc to avoid crashes)
        with patch("legacy.services.user_service.user_service.get_or_create_user", new_callable=AsyncMock) as mock_user:
            mock_user.return_value = MagicMock(id=user_id)

            with patch("legacy.services.hp_service.hp_service.calculate_daily_drain", new_callable=AsyncMock):
                with patch("legacy.services.quest_service.quest_service.trigger_push_quests", new_callable=AsyncMock):
                    # MOCK THE TARGET SERVICE: QuestService
                    with patch(
                        "legacy.services.quest_service.quest_service.create_new_goal", new_callable=AsyncMock
                    ) as mock_create_goal:
                        mock_create_goal.return_value = (MagicMock(title="Become Strong"), {})

                        # EXECUTE
                        await handle_ai_analysis(mock_session, user_id, "I want to be strong")

                        # VERIFY
                        mock_create_goal.assert_called_once()
                        call_args = mock_create_goal.call_args
                        # (session, user_id, goal_text=...)
                        assert call_args.kwargs["goal_text"] == "Become Strong"


@pytest.mark.asyncio
async def test_deep_integration_start_challenge():
    """
    Verify 'start_challenge' tool call triggers create_quest.
    """
    mock_session = AsyncMock()
    user_id = "test_user_tool"

    mock_plan = AgentPlan(
        narrative="Challenge accepted.",
        tool_calls=[{"tool": "start_challenge", "args": {"title": "100 Pushups", "difficulty": "S"}}],
    )

    with patch(
        "application.services.brain_service.brain_service.think_with_session", new_callable=AsyncMock
    ) as mock_think:
        mock_think.return_value = mock_plan

        with patch("legacy.services.user_service.user_service.get_or_create_user", new_callable=AsyncMock):
            with patch("legacy.services.hp_service.hp_service.calculate_daily_drain", new_callable=AsyncMock):
                with patch("legacy.services.quest_service.quest_service.trigger_push_quests", new_callable=AsyncMock):
                    # MOCK THE TARGET SERVICE
                    with patch(
                        "legacy.services.quest_service.quest_service.create_quest", new_callable=AsyncMock
                    ) as mock_create_quest:
                        # EXECUTE
                        await handle_ai_analysis(mock_session, user_id, "Challenge me")

                        # VERIFY
                        mock_create_quest.assert_called_once()
                        args = mock_create_quest.call_args.kwargs
                        assert args["title"] == "100 Pushups"
                        assert args["difficulty"] == "S"
