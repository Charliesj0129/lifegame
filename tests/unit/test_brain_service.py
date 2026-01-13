import pytest
from unittest.mock import AsyncMock, MagicMock
from application.services.brain_service import BrainService, AgentPlan


@pytest.fixture
def mock_context_service():
    mock = MagicMock()
    mock.get_working_memory = AsyncMock(
        return_value={
            "user_state": {"level": 1, "churn_risk": "LOW"},
            "time_context": "2024-01-01 12:00:00 UTC",
            "short_term_history": "- Log 1\n- Log 2",
            "long_term_context": [],
        }
    )
    return mock


@pytest.fixture
def mock_flow_controller():
    mock = MagicMock()
    mock.calculate_next_state.return_value = MagicMock(
        difficulty_tier="D", narrative_tone="Encouraging", loot_multiplier=1.0
    )
    return mock


@pytest.fixture
def mock_ai_engine():
    mock = MagicMock()
    mock.generate_json = AsyncMock(
        return_value={
            "narrative": "Test Response",
            "stat_update": {"stat_type": "STR", "xp_amount": 10, "hp_change": 0, "gold_change": 0},
        }
    )
    return mock


@pytest.mark.asyncio
async def test_brain_think_with_pulse(mock_context_service, mock_flow_controller, mock_ai_engine, monkeypatch):
    # Mock Dependencies
    monkeypatch.setattr("application.services.brain_service.context_service", mock_context_service)
    monkeypatch.setattr("application.services.brain_service.flow_controller", mock_flow_controller)
    monkeypatch.setattr("application.services.brain_service.ai_engine", mock_ai_engine)

    bs = BrainService()
    session = AsyncMock()

    # Pulse Events
    pulsed_events = {"drain_amount": 50, "viper_taunt": "Where have you been?"}

    plan = await bs.think_with_session(session, "user1", "I am back", pulsed_events=pulsed_events)

    assert isinstance(plan, AgentPlan)
    assert plan.narrative == "Test Response"

    # Check if Alerts were injected into AI Prompt
    # We inspect the call args of ai_engine.generate_json
    args, _ = mock_ai_engine.generate_json.call_args
    system_prompt = args[0]

    assert "ALERTS" in system_prompt
    assert "HP Drained: 50" in system_prompt
    assert "Where have you been?" in system_prompt
