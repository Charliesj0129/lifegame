import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from application.services.brain_service import brain_service
from application.services.context_service import context_service

@pytest.mark.asyncio
async def test_cognitive_architecture_flow():
    """
    Verify that the Brain uses Identity Context and Dynamic Flow.
    """
    # 1. Mock Session & Context
    mock_session = AsyncMock()
    user_id = "test_socratic_user"
    
    # Mock efficient Context Service return to avoid DB calls
    with patch.object(context_service, "get_working_memory", new_callable=AsyncMock) as mock_mem:
        mock_mem.return_value = {
            "user_state": {"level": 5, "churn_risk": "LOW", "current_tier": "B"},
            "time_context": "2026-01-13 12:00:00 UTC",
            "short_term_history": "- Login (10m ago)",
            "long_term_context": [],
            "identity_context": {
                "core_values": ["Wisdom", "Discipline"],
                "identity_tags": ["Stoic Philosopher"]
            }
        }
        
        # 2. Mock AI Engine to return valid plan
        with patch("legacy.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = {
                "narrative": "What is the nature of your request?",
                "stat_update": {"xp_amount": 20}
            }
            
            # 3. Execute Think
            plan = await brain_service.think_with_session(mock_session, user_id, "What use are you?")
            
            # 4. Verification
            # a. Check if Identity was injected into Prompt
            call_args = mock_ai.call_args[0]
            system_prompt = call_args[0]
            
            assert "The Socratic Architect" in system_prompt
            assert "Wisdom, Discipline" in system_prompt
            assert "Stoic Philosopher" in system_prompt
            
            # b. Check Dynamic Flow (Target Tier B from user_state)
            assert plan.flow_state["tier"] == "B"
            
            # c. Check Response
            assert plan.narrative == "What is the nature of your request?"

@pytest.mark.asyncio
async def test_cognitive_fallback():
    """
    Verify immersive fallback.
    """
    mock_session = AsyncMock()
    with patch.object(context_service, "get_working_memory", new_callable=AsyncMock) as mock_mem:
        mock_mem.return_value = {
            "user_state": {},
            "time_context": "2026-01-13 12:00:00 UTC",
            "short_term_history": "",
            "long_term_context": [],
            "identity_context": {}
        }
        
        # Force AI Failure
        with patch("legacy.services.ai_engine.ai_engine.generate_json", side_effect=Exception("AI Down")):
            plan = await brain_service.think_with_session(mock_session, "user", "Hello")
            
            assert "Cipher Interference" in plan.narrative
            assert plan.flow_state["error"] == "AI Down"
