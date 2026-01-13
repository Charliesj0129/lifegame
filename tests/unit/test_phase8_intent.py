import pytest
from application.services.brain_service import BrainService, AgentPlan, FlowState


@pytest.mark.unit
def test_classify_intent_logic():
    brain = BrainService()

    # Test Goal Creation
    assert brain._classify_intent("我要成為程式大師") == "CREATE_GOAL"
    assert brain._classify_intent("想學畫畫") == "CREATE_GOAL"
    assert brain._classify_intent("set new goal") == "CREATE_GOAL"

    # Test Challenge
    assert brain._classify_intent("挑戰 30 天不喝飲料") == "START_CHALLENGE"
    assert brain._classify_intent("開始任務") == "START_CHALLENGE"

    # Test Greeting
    assert brain._classify_intent("Hello") == "GREETING"
    assert brain._classify_intent("早安") == "GREETING"

    # Test Unknown
    assert brain._classify_intent("今天天氣不錯") == "UNKNOWN"


@pytest.mark.unit
def test_system_prompt_injection():
    brain = BrainService()
    dummy_memory = {
        "user_state": {"level": 1, "churn_risk": "LOW"},
        "time_context": "Morning",
        "short_term_history": "",
        "long_term_context": [],
        "recent_ai_actions": [],
    }
    dummy_flow = FlowState(difficulty_tier="C", narrative_tone="balanced", loot_multiplier=1.0)

    # Test with Hint
    prompt = brain._construct_system_prompt(dummy_memory, dummy_flow, intent_hint="CREATE_GOAL")
    assert "Detected Intent: CREATE_GOAL" in prompt
    assert "SYSTEM HINT: User likely wants to set a GOAL" in prompt

    # Test without Hint
    prompt_normal = brain._construct_system_prompt(dummy_memory, dummy_flow, intent_hint="UNKNOWN")
    assert "Detected Intent: UNKNOWN" in prompt_normal
    assert "SYSTEM HINT: User likely wants to set a GOAL" not in prompt_normal
