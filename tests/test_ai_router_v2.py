import pytest
from unittest.mock import AsyncMock, patch
from app.services.ai_service import AIService
from app.models.user import User
from app.models.quest import Rival

@pytest.mark.asyncio
async def test_router_chain_of_thought():
    # Mock dependencies
    mock_session = AsyncMock()
    
    # Mock User/Rival logs
    with patch("app.services.user_service.user_service.get_or_create_user", new_callable=AsyncMock) as mock_get_user, \
         patch("app.services.rival_service.rival_service.get_or_create_rival", new_callable=AsyncMock) as mock_get_rival, \
         patch("app.services.ai_service.AIService._get_history", new_callable=AsyncMock) as mock_hist, \
         patch("app.services.ai_service.AIService._save_log", new_callable=AsyncMock), \
         patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
         
        mock_get_user.return_value = User(id="u1", level=5, streak_count=2)
        mock_get_rival.return_value = Rival(id="r1", level=3)
        mock_hist.return_value = "User: Hi"
        
        # Mock AI Response: CoT Plan
        mock_ai.return_value = {
            "thought": "User is tired and hurt.",
            "plan": [
                {"tool": "use_item", "arguments": {"item_name": "Potion"}},
                {"tool": "log_action", "arguments": {"text": "Sleep"}}
            ]
        }
        
        from linebot.v3.messaging import TextMessage
        # Mock Tools
        with patch("app.services.tool_registry.tool_registry.use_item", new_callable=AsyncMock) as mock_use, \
             patch("app.services.tool_registry.tool_registry.log_action", new_callable=AsyncMock) as mock_log:
             
            mock_use.return_value = ({"hp": 10}, TextMessage(text="Used Potion"))
            mock_log.return_value = ({"xp": 5}, TextMessage(text="Slept well"))
            
            # Execute
            msg, tool, data = await AIService.router(mock_session, "u1", "Heal and sleep")
            
            # Verify Calls
            assert mock_use.called
            assert mock_use.call_args[0][2] == "Potion"
            
            assert mock_log.called
            assert mock_log.call_args[0][2] == "Sleep"
            
            # Verify Return: Should contain partial text from both?
            # Current implementation logic: 
            # if len(results) > 1: combined_text...
            assert "Used Potion" in msg.text
            assert "Slept well" in msg.text

@pytest.mark.asyncio
async def test_router_fuzzy_advice():
    # Mock dependencies
    mock_session = AsyncMock()
    with patch("app.services.user_service.user_service.get_or_create_user", new_callable=AsyncMock) as mock_get_user, \
         patch("app.services.rival_service.rival_service.get_or_create_rival", new_callable=AsyncMock) as mock_get_rival, \
         patch("app.services.ai_service.AIService._get_history", new_callable=AsyncMock) as mock_hist, \
         patch("app.services.ai_service.AIService._save_log", new_callable=AsyncMock), \
         patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
         
        mock_get_user.return_value = User(id="u1", level=5)
        mock_get_rival.return_value = Rival(id="r1", level=3)
        mock_hist.return_value = ""
        
        # Mock AI Response: Fuzzy Advice
        mock_ai.return_value = {
            "thought": "User is burnout.",
            "tool": "give_advice",
            "arguments": {"topic": "Burnout"}
        }
        
        # Execute
        msg, tool, data = await AIService.router(mock_session, "u1", "I am tired")
        
        # Verify
        assert tool == "give_advice"
        assert "Advisor: Burnout" in msg.text
