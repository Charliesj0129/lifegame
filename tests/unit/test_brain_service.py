import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from application.services.brain_service import BrainService, AgentPlan
from application.services.context_service import ContextService
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

@pytest_asyncio.fixture
async def mock_dependencies():
    from unittest.mock import patch
    
    # Mock AI Engine
    with patch("application.services.brain_service.ai_engine") as mock_ai, \
         patch("application.services.brain_service.context_service") as mock_ctx:
        
        mock_ai.generate_json = AsyncMock(return_value={
            "narrative": "Test Narrative",
            "stat_update": {"stat_type": "STR", "xp_amount": 50, "hp_change": 0, "gold_change": 10},
            "tool_calls": []
        })
        
        mock_ctx.get_working_memory = AsyncMock(return_value={
            "user_state": {"level": 1, "churn_risk": "LOW"},
            "time_context": "2026-01-01",
            "short_term_history": "",
            "long_term_context": []
        })
        
        yield mock_ai, mock_ctx

@pytest.mark.asyncio
async def test_brain_think_flow(mock_dependencies):
    mock_ai, mock_ctx = mock_dependencies
    
    brain = BrainService()
    # Mock session (not used by mocking context_service, but passed in signature)
    session = MagicMock()
    
    plan = await brain.think_with_session(session, "user1", "I ran 5km")
    
    # Verify Schema
    assert isinstance(plan, AgentPlan)
    assert plan.narrative == "Test Narrative"
    assert plan.stat_update.xp_amount == 50
    assert plan.flow_state["tier"] in ["C", "B", "A", "D", "E"] # Default C
    
    # Verify Interactions
    mock_ctx.get_working_memory.assert_called_once()
    mock_ai.generate_json.assert_called_once()
    
    # Check Prompt Construction (Indirectly)
    call_args = mock_ai.generate_json.call_args[0]
    system_prompt = call_args[0]
    assert "LifeOS-RPG Game Master" in system_prompt
    assert "Narrative Tone:" in system_prompt
