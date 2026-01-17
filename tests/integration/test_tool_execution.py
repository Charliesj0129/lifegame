import pytest
import sys
from unittest.mock import AsyncMock, patch, MagicMock

# --- MOCK KUZU BEFORE IMPORTS ---
mock_kuzu_mod = MagicMock()
sys.modules["kuzu"] = mock_kuzu_mod
mock_adapter_mod = MagicMock()
sys.modules["adapters.persistence.kuzu.adapter"] = mock_adapter_mod


# ----------------------------------------

sys.modules["deepdiff"] = MagicMock()
sys.modules["chromadb"] = MagicMock()
sys.modules["adapters.persistence.chroma.adapter"] = MagicMock()
# --------------------------------

from app.main import handle_ai_analysis
from application.services.brain_service import AgentPlan


@pytest.fixture(autouse=True)
def mock_tool_kuzu():
    mock_kuzu_instance = MagicMock()
    mock_kuzu_instance.query_recent_context = AsyncMock(return_value=[])
    mock_kuzu_instance.record_user_event = AsyncMock()
    
    # Patch ContextService
    from application.services.context_service import context_service
    original_kuzu = context_service.kuzu
    context_service.kuzu = mock_kuzu_instance
    
    # Patch Container
    import app.core.container
    original_get_adapter = getattr(app.core.container, "get_kuzu_adapter", None)
    app.core.container.get_kuzu_adapter = MagicMock(return_value=mock_kuzu_instance)
    
    yield
    
    context_service.kuzu = original_kuzu
    if original_get_adapter:
        app.core.container.get_kuzu_adapter = original_get_adapter
    else:
        del app.core.container.get_kuzu_adapter

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
        "application.services.brain_service.BrainService.think_with_session", new_callable=AsyncMock
    ) as mock_think:
        mock_think.return_value = mock_plan

        # Mock Dependencies (User, HP, etc to avoid crashes)
        from app.core.container import container
        mock_user_svc = MagicMock()
        mock_user_svc.get_or_create_user = AsyncMock(return_value=MagicMock(id=user_id))
        container._user_service = mock_user_svc
        
        try:
            with patch("application.services.hp_service.hp_service.calculate_daily_drain", new_callable=AsyncMock) as mock_drain:
                mock_drain.return_value = 0
                with patch("application.services.quest_service.quest_service.trigger_push_quests", new_callable=AsyncMock):
                    # MOCK THE TARGET SERVICE: QuestService
                    with patch(
                        "application.services.quest_service.quest_service.create_new_goal", new_callable=AsyncMock
                    ) as mock_create_goal:
                        mock_create_goal.return_value = (MagicMock(title="Become Strong"), {})



                        # EXECUTE
                        await handle_ai_analysis(mock_session, user_id, "I want to be strong")

                        # VERIFY
                        mock_create_goal.assert_called_once()
                        call_args = mock_create_goal.call_args
                        # (session, user_id, goal_text=...)
                        assert call_args.kwargs["goal_text"] == "Become Strong"
        finally:
            container._user_service = None


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
        "application.services.brain_service.BrainService.think_with_session", new_callable=AsyncMock
    ) as mock_think:
        mock_think.return_value = mock_plan

        from app.core.container import container
        mock_user_svc = MagicMock()
        mock_user_svc.get_or_create_user = AsyncMock()
        container._user_service = mock_user_svc

        try:
            with patch("application.services.hp_service.hp_service.calculate_daily_drain", new_callable=AsyncMock) as mock_drain:
                mock_drain.return_value = 0
                with patch("application.services.quest_service.quest_service.trigger_push_quests", new_callable=AsyncMock):
                    # MOCK THE TARGET SERVICE
                    with patch(
                        "application.services.quest_service.quest_service.create_quest", new_callable=AsyncMock
                    ) as mock_create_quest:


                        # EXECUTE
                        await handle_ai_analysis(mock_session, user_id, "Challenge me")

                        # VERIFY
                        mock_create_quest.assert_called_once()
                        args = mock_create_quest.call_args.kwargs
                        assert args["title"] == "100 Pushups"
                        assert args["difficulty"] == "S"
        finally:
            container._user_service = None
