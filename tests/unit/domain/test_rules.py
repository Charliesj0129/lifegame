from datetime import date, timedelta
from domain.rules.rival_rules import RivalRules
from domain.rules.health_rules import HealthRules, HPStatus

def test_rival_inactivity_penalty():
    today = date(2025, 1, 10)
    # Case 1: Active yesterday (1 day diff, 0 missed)
    last_active = date(2025, 1, 9)
    result = RivalRules.calculate_inactivity_penalty(
        last_active, today, 1000, 100, 5, 5, 500
    )
    assert result.missed_days == 0
    assert result.rival_xp_gain == 0

    # Case 2: Missed 2 days (Active on 1/7, today is 1/10. Days: 8, 9 missed)
    # Delta = 3 days. Missed = 3 - 1 = 2
    last_active = date(2025, 1, 7)
    result = RivalRules.calculate_inactivity_penalty(
        last_active, today, 1000, 100, 5, 5, 500
    )
    assert result.missed_days == 2
    assert result.rival_xp_gain == 200 # 100 * 2
    assert result.theft_xp == 100 # 1000 * 0.05 * 2 = 100
    assert result.theft_gold == 10 # 100 * 0.05 * 2 = 10

def test_health_status_logic():
    assert HealthRules.determine_status(0) == HPStatus.HOLLOWED
    assert HealthRules.determine_status(29) == HPStatus.CRITICAL
    assert HealthRules.determine_status(30) == HPStatus.HEALTHY
    
    # Recovering Logic
    assert HealthRules.determine_status(10, was_hollowed=True) == HPStatus.RECOVERING
