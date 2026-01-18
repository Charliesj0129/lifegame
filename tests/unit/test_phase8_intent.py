import pytest
from application.services.brain.narrator_service import NarratorService, AgentPlan
from application.services.brain.flow_controller import FlowState


@pytest.mark.unit
def test_classify_intent_logic():
    narrator = NarratorService()

    # Test Goal Creation
    assert narrator._classify_intent("我要成為程式大師") == "CREATE_GOAL"
    assert narrator._classify_intent("想學畫畫") == "CREATE_GOAL"
    assert narrator._classify_intent("set new goal") == "CREATE_GOAL"

    # Test Challenge
    assert narrator._classify_intent("挑戰 30 天不喝飲料") == "START_CHALLENGE"
    assert narrator._classify_intent("開始任務") == "START_CHALLENGE"

    # Test Greeting
    assert narrator._classify_intent("Hello") == "GREETING"
    assert narrator._classify_intent("早安") == "GREETING"

    # Test Unknown
    assert narrator._classify_intent("今天天氣不錯") == "UNKNOWN"


@pytest.mark.unit
def test_system_prompt_injection():
    narrator = NarratorService()
    dummy_memory = {
        "user_state": {"level": 1, "churn_risk": "LOW"},
        "time_context": "Morning",
        "short_term_history": "",
        "long_term_context": [],
        "recent_ai_actions": [],
    }
    dummy_flow = FlowState(difficulty_tier="C", narrative_tone="balanced", loot_multiplier=1.0)

    # Test with Hint
    prompt = narrator._construct_system_prompt(dummy_memory, dummy_flow, intent_hint="CREATE_GOAL")
    assert "Detected Intent: CREATE_GOAL" in prompt
    assert "SYSTEM HINT: User likely wants to set a GOAL" in prompt

    # Test without Hint
    prompt_normal = narrator._construct_system_prompt(dummy_memory, dummy_flow, intent_hint="UNKNOWN")
    assert "Detected Intent: UNKNOWN" in prompt_normal
    assert "SYSTEM HINT: User likely wants to set a GOAL" not in prompt_normal
