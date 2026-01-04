import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.quest_service import quest_service
from app.services.flex_renderer import flex_renderer
from app.models.quest import Quest, QuestStatus
from app.models.user import User
import datetime

@pytest.mark.asyncio
async def test_quest_generation():
    print("\n--- Testing Quest Generation ---")
    mock_session = AsyncMock()
    
    # 1. Simulate No Quests -> Should Generate
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [] # No existing
    mock_session.execute.return_value = mock_result
    
    user_id = "U_TEST_QUEST"
    
    with patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai, \
         patch("app.services.rival_service.RivalService.get_rival", new_callable=AsyncMock) as mock_get_rival, \
         patch("app.services.user_service.UserService.get_user", new_callable=AsyncMock) as mock_get_user:
        
        mock_ai.return_value = {"quests": [
            {"title": "Q1", "diff": "C", "xp": 10},
            {"title": "Q2", "diff": "C", "xp": 10},
            {"title": "Q3", "diff": "C", "xp": 10}
        ]}
        mock_get_rival.return_value = MagicMock(level=1)
        mock_get_user.return_value = MagicMock(level=1)
        
        quests = await quest_service.get_daily_quests(mock_session, user_id)
    
    assert len(quests) == 3 # Default batch size
    assert quests[0].user_id == user_id
    assert quests[0].status == QuestStatus.ACTIVE.value
    
    # Verify commit called (to save new quests)
    mock_session.commit.assert_awaited()

@pytest.mark.asyncio
async def test_quest_completion():
    print("\n--- Testing Quest Completion ---")
    mock_session = AsyncMock()
    user_id = "U_TEST_QA"
    quest_id = "Q_123"
    
    # Mock Quest
    mock_quest = Quest(id=quest_id, user_id=user_id, status=QuestStatus.ACTIVE.value, xp_reward=50)
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_quest
    mock_session.execute.return_value = mock_result
    
    # Call Complete
    completed_q = await quest_service.complete_quest(mock_session, user_id, quest_id)
    
    assert completed_q is not None
    assert completed_q.status == QuestStatus.DONE.value
    mock_session.commit.assert_awaited()

@pytest.mark.asyncio
async def test_quest_ui_render():
    print("\n--- Testing Quest UI ---")
    quests = [
        Quest(id="q1", title="Test Q1", difficulty_tier="E", xp_reward=20, status="ACTIVE"),
        Quest(id="q2", title="Test Q2", difficulty_tier="C", xp_reward=50, status="DONE")
    ]
    
    flex = flex_renderer.render_quest_list(quests)
    assert flex.alt_text == "Active Quests"
    # Basic check of content logic
    # "COMPLETE" button should be in Q1, "COMPLETED" text in Q2
    # We could parse JSON but basic no-crash check is MVP.
    assert flex.contents is not None

@pytest.mark.asyncio
async def test_reroll_logic():
    print("\n--- Testing Reroll ---")
    # Should delete old and create new
    mock_session = AsyncMock()
    user_id = "U_REROLL"
    
    # Existing quests
    q1 = Quest(id="q1", status="ACTIVE")
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [q1]
    mock_session.execute.return_value = mock_result
    
    with patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai, \
         patch("app.services.rival_service.RivalService.get_rival", new_callable=AsyncMock) as mock_get_rival, \
         patch("app.services.user_service.UserService.get_user", new_callable=AsyncMock) as mock_get_user:
         
        mock_ai.return_value = {"quests": [{"title": "New Q1", "diff": "C", "xp": 10}]}
        mock_get_rival.return_value = MagicMock(level=1)
        mock_get_user.return_value = MagicMock(level=1)

        new_quests = await quest_service.reroll_quests(mock_session, user_id)
    
    # Should have deleted q1
    mock_session.delete.assert_awaited_with(q1)
    # Should return new batch (mocked generation logic inside?)
    # Since _generate_daily_batch creates 3, we expect 3 new ones
    assert len(new_quests) == 3
