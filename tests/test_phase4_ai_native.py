import pytest
from unittest.mock import AsyncMock, patch
from app.services.ai_service import AIService
from app.models.user import User
from app.models.quest import Rival

@pytest.mark.asyncio
async def test_memory_persistence(db_session):
    """Verify that chat logs are saved and retrieved correctly."""
    user_id = "mem_test_user"
    
    # 1. Save logs
    await AIService._save_log(db_session, user_id, "user", "Hello AI")
    await AIService._save_log(db_session, user_id, "assistant", "Hello User")
    
    # 2. Retrieve history
    history = await AIService._get_history(db_session, user_id, limit=5)
    
    assert "user: Hello AI" in history
    assert "assistant: Hello User" in history

@pytest.mark.asyncio
async def test_router_status_intent(db_session):
    """Verify router calls get_status when AI detects intent."""
    user_id = "router_test_user"
    
    # Mock Class Methods (since services are instances)
    with patch("app.services.user_service.UserService.get_or_create_user", new_callable=AsyncMock) as mock_get_user, \
         patch("app.services.rival_service.RivalService.get_or_create_rival", new_callable=AsyncMock) as mock_get_rival, \
         patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_gen_json, \
         patch("app.services.tool_registry.ToolRegistry.get_status", new_callable=AsyncMock) as mock_tool_status:
        
        mock_get_user.return_value = User(id=user_id, level=5)
        mock_get_rival.return_value = Rival(user_id=user_id, level=1)
        
        # Mock AI Response
        mock_gen_json.return_value = {
            "thought": "User wants status",
            "tool": "get_status",
            "arguments": {}
        }
        
        mock_tool_status.return_value = ({"status": "ok"}, "Status Message")
        
        # Act
        msg, tool, _ = await AIService.router(db_session, user_id, "Show me my stats")
        
        # Assert
        assert tool == "get_status"
        mock_tool_status.assert_called_once()
        mock_gen_json.assert_called_once()

@pytest.mark.asyncio
async def test_router_inventory_fallback(db_session):
    """Verify router defaults to logging if tool is unknown."""
    user_id = "router_fallback_user"
    
    with patch("app.services.user_service.UserService.get_or_create_user", new_callable=AsyncMock) as mock_get_user, \
         patch("app.services.rival_service.RivalService.get_or_create_rival", new_callable=AsyncMock) as mock_get_rival, \
         patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_gen_json, \
         patch("app.services.tool_registry.ToolRegistry.log_action", new_callable=AsyncMock) as mock_log_action:
             
        mock_get_user.return_value = User(id=user_id, level=5)
        mock_get_rival.return_value = Rival(user_id=user_id, level=1)
        
        # Mock AI returning garbage tool
        mock_gen_json.return_value = {
            "thought": "Confused",
            "tool": "unknown_tool_xyz",
            "arguments": {}
        }
        
        mock_log_action.return_value = ({"result": "logged"}, "Log Message")
        
        # Act
        msg, tool, _ = await AIService.router(db_session, user_id, "Some random text")
        
        # Assert
        # Unknown tools are ignored; router should fall back to log_action
        assert tool == "log_action"
        mock_log_action.assert_called_once() 

@pytest.mark.asyncio
async def test_router_multi_tool_calls(db_session):
    """Verify router can execute multiple tool calls in order."""
    user_id = "router_multi_user"

    with patch("app.services.user_service.UserService.get_or_create_user", new_callable=AsyncMock) as mock_get_user, \
         patch("app.services.rival_service.RivalService.get_or_create_rival", new_callable=AsyncMock) as mock_get_rival, \
         patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_gen_json, \
         patch("app.services.tool_registry.ToolRegistry.use_item", new_callable=AsyncMock) as mock_use_item, \
         patch("app.services.tool_registry.ToolRegistry.log_action", new_callable=AsyncMock) as mock_log_action:

        mock_get_user.return_value = User(id=user_id, level=5)
        mock_get_rival.return_value = Rival(user_id=user_id, level=1)

        mock_gen_json.return_value = {
            "thought": "Two actions in order.",
            "tool_calls": [
                {"tool": "use_item", "arguments": {"item_name": "potion"}},
                {"tool": "log_action", "arguments": {"text": "I'm tired and going to sleep"}}
            ],
            "response_voice": "Mentor",
            "confidence": 0.64
        }

        mock_use_item.return_value = ({"result": "used"}, "Item Message")
        mock_log_action.return_value = ({"result": "logged"}, "Log Message")

        messages, tools, result = await AIService.router(db_session, user_id, "I'm tired, drink a potion and sleep")

        assert tools == ["use_item", "log_action"]
        assert messages == ["Item Message", "Log Message"]
        assert result.get("response_voice") == "Mentor"
        assert result.get("tool_results")[0]["result"] == "used"
