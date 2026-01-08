import pytest
import sys
from unittest.mock import AsyncMock, patch, MagicMock

# --- MOCK DEPENDENCIES BEFORE IMPORTING APP ---
# This prevents app.main -> ... -> KuzuAdapter from trying to open the locked DB
mock_kuzu = MagicMock()
sys.modules["kuzu"] = mock_kuzu
sys.modules["adapters.persistence.kuzu.adapter"] = MagicMock()
# Also mock legacy services that might trigger DB
sys.modules["legacy.services.quest_service"] = MagicMock()
# ---------------------------------------------

from app.main import process_game_logic
from domain.models.game_result import GameResult

@pytest.mark.asyncio
async def test_process_game_logic_attack():
    """Test 'attack' command triggers specific handler"""
    # Mock services used by game_loop
    with patch("application.services.game_loop.user_service") as mock_user_svc, \
         patch("application.services.game_loop.rival_service") as mock_rival_svc, \
         patch("application.services.game_loop.hp_service") as mock_hp_svc, \
         patch("app.main.AsyncSessionLocal") as mock_session_cls:
        
        # Setup Mocks
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        mock_user = MagicMock()
        mock_user.is_hollowed = False
        mock_user.hp_status = "HEALTHY"
        # Mocking async method requires AsyncMock or side_effect logic
        mock_user_svc.get_or_create_user = AsyncMock(return_value=mock_user)
        
        mock_rival_svc.process_encounter = AsyncMock(return_value="") 
        
        # Execute
        result = await process_game_logic("test_user_id", "attack")
        
        # Verify
        assert isinstance(result, GameResult)
        assert "發動了攻擊" in result.text
        assert result.intent == "attack"

@pytest.mark.asyncio
async def test_process_game_logic_defend():
    """Test 'defend' command triggers specific handler"""
    with patch("application.services.game_loop.user_service") as mock_user_svc, \
         patch("application.services.game_loop.rival_service") as mock_rival_svc, \
         patch("app.main.AsyncSessionLocal") as mock_session_cls:
        
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        mock_user = MagicMock(is_hollowed=False, hp_status="HEALTHY")
        mock_user_svc.get_or_create_user = AsyncMock(return_value=mock_user)
        mock_rival_svc.process_encounter = AsyncMock(return_value="")
        
        result = await process_game_logic("test_user_id", "defend")
        
        assert "防禦姿態" in result.text
        assert result.intent == "defend"

@pytest.mark.asyncio
async def test_process_game_logic_unknown():
    """Test unknown command returns default response"""
    with patch("application.services.game_loop.user_service") as mock_user_svc, \
         patch("application.services.game_loop.rival_service") as mock_rival_svc, \
         patch("app.main.AsyncSessionLocal") as mock_session_cls:
         
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_user = MagicMock(is_hollowed=False, hp_status="HEALTHY")
        mock_user_svc.get_or_create_user = AsyncMock(return_value=mock_user)
        mock_rival_svc.process_encounter = AsyncMock(return_value="")

        # Default fallback in dispatcher returns "無法處理此請求"
        result = await process_game_logic("test_user_id", "unknown_command_xyz")
        
        assert "無法處理" in result.text
