import pytest
from application.services.brain.flow_controller import FlowController

def test_pid_frustration():
    fc = FlowController()
    # Scenario: User is Frustrated (Fails 3 times) -> 0% win rate
    recent_perf = [False, False, False]
    
    state = fc.calculate_next_state("A", recent_perf)
    
    # Target 70%, Actual 0%. Error -0.7. Adjustment -1.
    # Current A(5) -> B(4)
    assert state.difficulty_tier == "B"
    assert state.narrative_tone == "Encourage"

def test_pid_boredom():
    fc = FlowController()
    # Scenario: Bored (5 Wins) -> 100% win rate
    recent_perf = [True, True, True, True, True]
    
    state = fc.calculate_next_state("C", recent_perf)
    
    # Target 70%, Actual 100%. Error +0.3. Adjustment +1.
    # Current C(3) -> B(4)
    assert state.difficulty_tier == "B"
    # Note: B is Higher than C in my map? 
    # TIER_VALUES = {"E": 1, ... "A": 5, "S": 6}
    # Checks: C(3) + 1 = 4(B). Yes.
    assert state.narrative_tone == "Respect"

def test_eomm_churn_save():
    fc = FlowController()
    # Scenario: High Churn Risk
    state = fc.calculate_next_state("A", [False], churn_risk="HIGH")
    
    # Should force Easy mode
    assert state.difficulty_tier == "E"
    assert state.loot_multiplier >= 2.0

def test_ai_director_stress():
    fc = FlowController()
    # Scenario: High Stress
    state = fc.calculate_next_state("A", [True], stress_score=0.9)
    
    # Should force Relax
    assert state.difficulty_tier == "D"
    assert state.narrative_tone == "Relax"

def test_fogg_calculator():
    fc = FlowController()
    
    # Scenario 1: Low M, High Friction
    # M=0.2 (Low), F=0.8 (Hard) -> A = 1.25. B = 0.2*1.25 = 0.25. Threshold 1.5. Fail.
    assert not fc.evaluate_fogg_trigger(0.2, 0.8)
    
    # Scenario 2: High M, Low Friction
    # M=0.8 (High), F=0.2 (Easy) -> A = 5.0. B = 0.8*5.0 = 4.0. Success.
    assert fc.evaluate_fogg_trigger(0.8, 0.2)
    
    # Scenario 3: Spark Trigger (Normal M, Low F)
    # M=0.5, F=0.3 -> A=3.33. B = 1.66. Success.
    assert fc.evaluate_fogg_trigger(0.5, 0.3)
