import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.quest_service import quest_service
from app.models.quest import Quest, Goal, GoalStatus
import json

@pytest.mark.asyncio
async def test_create_new_goal_with_ai():
    print("\n--- Testing AI Goal Decomposition ---")
    mock_session = AsyncMock()
    
    # Mock AI Response
    mock_plan = {
        "milestones": [
            {"title": "Learn Python Basics", "desc": "Variables and Loops", "difficulty": "C"},
            {"title": "Build a Script", "desc": "File I/O", "difficulty": "C"}
        ],
        "daily_habits": [{"title": "Code 30m", "desc": "Every day"}]
    }
    
    with patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = mock_plan
        
        user_id = "U_AI_TEST"
        goal_text = "Become a Developer"
        
        goal, plan = await quest_service.create_new_goal(mock_session, user_id, goal_text)
        
        # Verify Goal Created
        assert goal.title == goal_text
        assert goal.status == GoalStatus.ACTIVE.value
        assert goal.decomposition_json == mock_plan
        
        # Verify Milestones (Quests) added to session
        # We expect 1 Goal + 2 Quests added = 3 add calls? Or iterate args
        # check call_args_list of session.add
        
        found_milestones = 0
        for call in mock_session.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, Quest) and obj.quest_type == "MAIN":
                found_milestones += 1
                
        assert found_milestones == 2
        mock_session.commit.assert_awaited()

@pytest.mark.asyncio
async def test_generate_daily_quests_with_active_goal():
    print("\n--- Testing AI Daily Quest Gen ---")
    mock_session = AsyncMock()
    user_id = "U_AI_DAILY"
    
    # Mock Existing Goal
    mock_goal = Goal(title="Become a Runner", status="ACTIVE")
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_goal
    mock_session.execute.return_value = mock_result
    
    # Mock AI Response
    mock_daily = [
        {"title": "Run 1km", "desc": "Easy jog", "diff": "D", "xp": 30},
        {"title": "Stretch", "desc": "5 mins", "diff": "E", "xp": 10},
        {"title": "Hydrate", "desc": "Water", "diff": "E", "xp": 10}
    ]
    
    with patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai, \
         patch("app.services.rival_service.RivalService.get_rival", new_callable=AsyncMock) as mock_get_rival, \
         patch("app.services.user_service.UserService.get_user", new_callable=AsyncMock) as mock_get_user:
        
        mock_ai.return_value = [
            {"title": "Focused Work", "desc": "Focus", "diff": "D", "xp": 20},
            {"title": "Clean", "desc": "Clean", "diff": "E", "xp": 20},
            {"title": "Hydrate", "desc": "Drink", "diff": "F", "xp": 10}
        ]
        mock_get_rival.return_value = MagicMock(level=1)
        mock_get_user.return_value = MagicMock(level=1)
        
        quests = await quest_service._generate_daily_batch(mock_session, user_id)
        
        assert len(quests) == 3
        assert quests[0].title == "Focused Work" # Updated to match new mock_ai.return_value
        # Verify Context in prompt
        # User prompt should contain "Become a Runner"
        args, _ = mock_ai.call_args
        assert "Become a Runner" in args[1]
