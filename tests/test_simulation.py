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
    # Mock services used by game_loop AND app.main (which does local import)
    # Note: We must assign the mocks to variables in the 'as' clause correctly
    with (
        patch("application.services.game_loop.user_service") as mock_game_user_svc,
        patch("legacy.services.user_service.user_service") as mock_legacy_user_svc,
        patch("application.services.game_loop.rival_service") as mock_rival_svc,
        patch("application.services.game_loop.hp_service"),
        patch("app.main.AsyncSessionLocal") as mock_session_cls,
    ):
        # Setup Mocks
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        mock_user = MagicMock()
        mock_user.is_hollowed = False
        mock_user.hp_status = "HEALTHY"

        # Configure BOTH mocks
        mock_game_user_svc.get_or_create_user = AsyncMock(return_value=mock_user)
        mock_legacy_user_svc.get_or_create_user = AsyncMock(return_value=mock_user)

        mock_rival_svc.process_encounter = AsyncMock(return_value="")

        # Execute
        result = await process_game_logic("test_user_id", "attack")

        # Verify
        assert isinstance(result, GameResult)
        assert "⚔️" in result.text or "攻擊" in result.text
        assert result.intent == "attack"


@pytest.mark.asyncio
async def test_process_game_logic_defend():
    """Test 'defend' command triggers specific handler"""
    with (
        patch("application.services.game_loop.user_service") as mock_game_user_svc,
        patch("legacy.services.user_service.user_service") as mock_legacy_user_svc,
        patch("application.services.game_loop.rival_service") as mock_rival_svc,
        patch("app.main.AsyncSessionLocal") as mock_session_cls,
    ):
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        mock_user = MagicMock(is_hollowed=False, hp_status="HEALTHY")
        mock_game_user_svc.get_or_create_user = AsyncMock(return_value=mock_user)
        mock_legacy_user_svc.get_or_create_user = AsyncMock(return_value=mock_user)
        mock_rival_svc.process_encounter = AsyncMock(return_value="")

        result = await process_game_logic("test_user_id", "defend")

        assert "防禦姿態" in result.text
        assert result.intent == "defend"


@pytest.mark.asyncio
async def test_process_game_logic_unknown():
    """Test unknown command returns generated AI response or default"""
    with (
        patch("application.services.game_loop.user_service") as mock_game_user_svc,
        patch("legacy.services.user_service.user_service") as mock_legacy_user_svc,
        patch("application.services.game_loop.rival_service") as mock_rival_svc,
        patch("app.main.AsyncSessionLocal") as mock_session_cls,
    ):
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_user = MagicMock(is_hollowed=False, hp_status="HEALTHY")
        mock_game_user_svc.get_or_create_user = AsyncMock(return_value=mock_user)
        mock_legacy_user_svc.get_or_create_user = AsyncMock(return_value=mock_user)
        mock_rival_svc.process_encounter = AsyncMock(return_value="")

        # Currently, if unknown, the new AI Persona replies with narrative.
        # "偵測到未知的通訊協議..."
        result = await process_game_logic("test_user_id", "unknown_command_xyz")

        # Check if it returned a response (not crash)
        assert result.text is not None
        # Dopamine Arbiter returns strict warnings
        assert any(k in result.text for k in ["無法處理", "未知", "戰略", "警告", "偵測", "無效"])
