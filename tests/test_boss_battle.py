import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from app.services.quest_service import quest_service
from app.models.user import User
from app.models.quest import Rival, Quest

@pytest.mark.asyncio
async def test_boss_battle_trigger():
    session = AsyncMock()
    user_id = "test_user"
    
    # 1. Setup User and Strong Rival
    user = User(id=user_id, level=5)
    rival = Rival(id="VIPER", level=8) # +3 Levels -> Trigger Boss Mode (+2 is threshold)
    
    # Mocking Service Calls inside _generate_daily_batch
    # We need to mock user_service and rival_service calls?
    # Actually _generate_daily_batch imports them locally, so we need to patch them using where they are imported.
    # Because they are local imports inside the function, patching 'app.services.quest_service.user_service' won't work if they are imported as modules?
    # The code does: `from app.services.rival_service import rival_service`
    # So we patch `app.services.quest_service.rival_service` NO, that's assuming module level import.
    # Since it's inside the function, we have to patch where `app.services.rival_service` points to?
    # Actually, easy way: Mock the side effects of get_user and get_rival if we can.
    # But since they are local imports, it's hard to patch 'rival_service' variable.
    # We should patch `app.services.rival_service.RivalService.get_rival`?
    
    with patch("app.services.rival_service.RivalService.get_rival", new_callable=AsyncMock) as mock_get_rival, \
         patch("app.services.user_service.UserService.get_user", new_callable=AsyncMock) as mock_get_user, \
         patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
         
        mock_get_user.return_value = user
        mock_get_rival.return_value = rival
        
        # Mock AI Response for Boss Quest
        mock_ai.return_value = {
            "title": "Defeat Viper: System Purge",
            "desc": "Reboot OS.",
            "diff": "S",
            "xp": 500
        }
        
        # Run
        quests = await quest_service._generate_daily_batch(session, user_id)
        
        # Assert
        assert len(quests) == 1
        q = quests[0]
        assert q.difficulty_tier == "S"
        assert q.is_redemption == True
        assert q.xp_reward == 500
        assert "System Purge" in q.title

@pytest.mark.asyncio
async def test_normal_quest_gen_no_boss():
    session = AsyncMock()
    user_id = "test_user"
    
    user = User(id=user_id, level=5)
    rival = Rival(id="VIPER", level=5) # Same Level -> No Boss
    
    with patch("app.services.rival_service.RivalService.get_rival", new_callable=AsyncMock) as mock_get_rival, \
         patch("app.services.user_service.UserService.get_user", new_callable=AsyncMock) as mock_get_user, \
         patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
         
        mock_get_user.return_value = user
        mock_get_rival.return_value = rival
        
        mock_ai.return_value = [
            {"title": "Task 1", "desc": "d", "diff": "D", "xp": 20},
            {"title": "Task 2", "desc": "d", "diff": "E", "xp": 20},
            {"title": "Task 3", "desc": "d", "diff": "C", "xp": 20}
        ]
        
        # Mock finding NO active goal
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        session.execute.return_value = mock_result

        quests = await quest_service._generate_daily_batch(session, user_id)
        
        assert len(quests) == 3
        assert quests[0].difficulty_tier != "S"
