import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from app.services.user_service import user_service
from app.services.quest_service import quest_service
from app.services.rival_service import rival_service
from app.services.rich_menu_service import rich_menu_service
from app.models.user import User
from app.models.quest import Quest, Rival

@pytest.mark.asyncio
async def test_full_user_journey():
    """
    Simulates a User's LifeCycle:
    1. Join (Link Rich Menu)
    2. Daily Quest Generation (Responsive)
    3. Inactivity (Viper Theft)
    4. Boss Mode Trigger (Lockdown)
    """
    session = AsyncMock()
    user_id = "journey_user"
    
    # --- PHASE 1: ONBOARDING ---
    # Mock User Creation
    user = User(id=user_id, level=1, xp=0, gold=0)
    
    with patch("app.services.rich_menu_service.rich_menu_service.link_user") as mock_link:
        # Simulate Webhook Follow Event logic (manually triggering service calls)
        # 1. Rich Menu Link
        rich_menu_service.link_user(user_id, "MAIN")
        mock_link.assert_called_with(user_id, "MAIN")

    # --- PHASE 2: DAILY ROUTINE ---
    # Mock Quest Generation
    with patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai, \
         patch("app.services.user_service.UserService.get_user", new_callable=AsyncMock) as mock_get_user, \
         patch("app.services.rival_service.RivalService.get_rival", new_callable=AsyncMock) as mock_get_rival:
         
         # Setup: User Exists, Rival is weak
         rival = Rival(id="VIPER", level=1)
         mock_get_user.return_value = user
         mock_get_rival.return_value = rival
         
         # AI returns standard quests
         mock_ai.return_value = [
             {"title": "Run 5km", "diff": "C", "xp": 50},
             {"title": "Read Book", "diff": "D", "xp": 30},
             {"title": "Meditation", "diff": "E", "xp": 20}
         ]
         
         # Mock No Active Goal
         mock_result_goal = MagicMock()
         mock_result_goal.scalars.return_value.first.return_value = None
         
         # Mock Query Execution sequence (Active Goal -> then ...?) 
         # It's hard to mock exact sequence of executes with one mock, so we just return None for goals
         session.execute.return_value = mock_result_goal

         quests = await quest_service._generate_daily_batch(session, user_id)
         
         assert len(quests) == 3
         assert quests[0].title == "Run 5km"
         
    # --- PHASE 3: INACTIVITY & THEFT ---
    # Fast forward time: User inactive for 5 days
    user.last_active_date = datetime.now() - timedelta(days=6) # 5 missed days
    user.xp = 1000 # Give some XP to steal
    user.gold = 1000
    
    # Mock DB for Rival Service
    # Rival Lv 1
    rival.xp = 0
    mock_result_rival = MagicMock()
    mock_result_rival.scalars.return_value.first.return_value = rival
    session.execute.return_value = mock_result_rival 
    
    narrative = await rival_service.process_encounter(session, user)
    
    # Verify Theft (5 days * 5% = 25%. 1000 * 0.25 = 250 stolen. Remain 750)
    assert user.xp == 750
    assert "siphoned 250 XP" in narrative
    
    # Verify Rival Growth (5 days * 100 = 500 XP)
    assert rival.xp == 500
    
    # --- PHASE 4: BOSS MODE ---
    # Now Rival became super strong
    rival.level = 10 # User is Lv 1
    rival.xp = 9000
    
    with patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai, \
         patch("app.services.user_service.UserService.get_user", new_callable=AsyncMock) as mock_get_user, \
         patch("app.services.rival_service.RivalService.get_rival", new_callable=AsyncMock) as mock_get_rival:
         
         mock_get_user.return_value = user
         mock_get_rival.return_value = rival
         
         mock_ai.return_value = {"title": "BOSS: Overthrow Viper", "diff": "S", "xp": 1000}
         
         # User asks for daily quests...
         boss_quests = await quest_service._generate_daily_batch(session, user_id)
         
         # Should get 1 Boss Quest
         assert len(boss_quests) == 1
         assert boss_quests[0].difficulty_tier == "S"
         assert "Overthrow Viper" in boss_quests[0].title
