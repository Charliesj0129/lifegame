import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from application.services.loot_service import loot_service, LootResult
from legacy.services.quest_service import quest_service
from legacy.models.quest import Quest, QuestStatus

@pytest.mark.asyncio
async def test_loot_service_rpe_calculation():
    """Verify LootService calculates RPE and variance correctly."""
    
    # Test Baseline (No Flow Mult, No Jackpot)
    # We mock random to be deterministic or just test bounds
    
    # Tier C Baseline = 50 XP
    loot = loot_service.calculate_reward("C", "C")
    assert loot.xp >= 40  # 50 * 0.8
    assert loot.xp <= 100 # Jackpot cap or 50 * 1.2 * 2 (if Jackpot)
    
    # Test Variance
    # We run multiple times to check for "Jackpot" or distinct values
    results = [loot_service.calculate_reward("C", "C").xp for _ in range(50)]
    assert len(set(results)) > 1, "Loot should have RNG variance"
    
    # Verify RPE Score Logic
    # Actual 50, Baseline 50 -> RPE 0
    # Actual 100 (Jackpot), Baseline 50 -> RPE 50
    with patch("random.uniform", return_value=1.0):
        with patch("random.random", return_value=1.0): # No jackpot
            loot_std = loot_service.calculate_reward("C", "C")
            assert loot_std.rpe_score == 0 # 50 - 50
            assert loot_std.narrative_flavor == "Standard"

@pytest.mark.asyncio
async def test_quest_service_complete_integration():
    """Verify complete_quest returns proper dict structure with Loot."""
    
    mock_session = AsyncMock()
    mock_quest = MagicMock(spec=Quest)
    mock_quest.id = "q1"
    mock_quest.user_id = "u1"
    mock_quest.difficulty_tier = "C"
    mock_quest.xp_reward = 50
    mock_quest.status = QuestStatus.ACTIVE.value
    mock_quest.quest_type = "SIDE"
    
    # Mock Select
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_quest
    mock_session.execute.return_value = mock_result
    
    # Mock User
    mock_user = MagicMock()
    mock_user.exp = 0  
    mock_user.xp = 0   # Fixed: Ensure xp exists
    mock_user.gold = 0 # Fixed: Ensure gold exists
    mock_user.level = 1
    mock_user.hp = 80
    mock_user.max_hp = 100
    mock_user.is_hollowed = False
    mock_user.hp_status = "NORMAL"
    # User service get_user
    with patch("legacy.services.user_service.user_service.get_user", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user
        
        # Mock Boss Service (ignore)
        with patch("legacy.services.boss_service.boss_service.deal_damage", new_callable=AsyncMock):
            
            result = await quest_service.complete_quest(mock_session, "u1", "q1")
            
            assert result is not None
            assert "quest" in result
            assert "loot" in result
            
            loot = result["loot"]
            assert isinstance(loot, LootResult)
            assert loot.xp > 0
            
            # Check User XP updated
            assert mock_user.xp == loot.xp
            assert mock_user.gold == loot.gold
            
            # Check Quest DONE
            assert mock_quest.status == QuestStatus.DONE.value
