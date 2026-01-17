import pytest
import sys
from unittest.mock import AsyncMock, patch, MagicMock

# --- MOCK DEPENDENCIES BEFORE IMPORTING APP ---
# This prevents app.main -> ... -> KuzuAdapter from trying to open the locked DB
mock_kuzu_mod = MagicMock()
sys.modules["kuzu"] = mock_kuzu_mod
mock_adapter_mod = MagicMock()
sys.modules["adapters.persistence.kuzu.adapter"] = mock_adapter_mod


# ----------------------------------------
sys.modules["deepdiff"] = MagicMock()
sys.modules["chromadb"] = MagicMock()
sys.modules["adapters.persistence.chroma.adapter"] = MagicMock()

# ---------------------------------------------

from app.main import process_game_logic
from domain.models.game_result import GameResult
from app.core.container import container


@pytest.fixture(autouse=True)
def mock_sim_kuzu():
    mock_kuzu_instance = MagicMock()
    mock_kuzu_instance.query_recent_context = AsyncMock(return_value=[])
    mock_kuzu_instance.record_user_event = AsyncMock()
    
    # Patch ContextService
    from application.services.context_service import context_service
    original_kuzu = context_service.kuzu
    context_service.kuzu = mock_kuzu_instance
    
    # Patch Container
    import app.core.container
    original_get_adapter = getattr(app.core.container, "get_kuzu_adapter", None)
    app.core.container.get_kuzu_adapter = MagicMock(return_value=mock_kuzu_instance)
    
    yield
    
    context_service.kuzu = original_kuzu
    if original_get_adapter:
        app.core.container.get_kuzu_adapter = original_get_adapter
    else:
        del app.core.container.get_kuzu_adapter

@pytest.mark.asyncio
async def test_process_game_logic_attack():
    """Test 'attack' command triggers specific handler"""
    # Use Container Injection
    mock_user_svc = AsyncMock()
    container._user_service = mock_user_svc


    with (
        patch("application.services.rival_service.rival_service") as mock_rival_svc,
        patch("application.services.game_loop.rival_service"),
        patch("application.services.game_loop.hp_service"),
        patch("app.main.AsyncSessionLocal") as mock_session_cls,
    ):
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        # Helper to ensure session.execute returns an object with scalars().all()
        mock_db_result = MagicMock()
        mock_db_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_db_result

        mock_user = MagicMock()
        mock_user.is_hollowed = False
        mock_user.hp_status = "HEALTHY"
        mock_user.level = 1


        mock_user_svc.get_or_create_user.return_value = mock_user
        mock_user_svc.get_user = AsyncMock(return_value=mock_user)
        
        # Ensure process_encounter is awaitable
        mock_rival_svc.process_encounter = AsyncMock(return_value="")

        # Execute
        result = await process_game_logic("test_user_id", "attack")

        # Verify
        assert isinstance(result, GameResult)
        assert "⚔️" in result.text or "攻擊" in result.text
        assert result.intent == "attack"

    # Cleanup
    container._user_service = None


@pytest.mark.asyncio
async def test_process_game_logic_defend():
    """Test 'defend' command triggers specific handler"""
    mock_user_svc = AsyncMock()
    container._user_service = mock_user_svc

    with (
        patch("application.services.rival_service.rival_service") as mock_rival_svc,
        patch("app.main.AsyncSessionLocal") as mock_session_cls,
    ):
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        mock_db_result = MagicMock()
        mock_db_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_db_result

        mock_user = MagicMock(is_hollowed=False, hp_status="HEALTHY", level=1)
        mock_user_svc.get_or_create_user.return_value = mock_user
        mock_user_svc.get_user = AsyncMock(return_value=mock_user)
        mock_rival_svc.process_encounter = AsyncMock(return_value="")

        result = await process_game_logic("test_user_id", "defend")

        assert "防禦姿態" in result.text
        assert result.intent == "defend"
    
    container._user_service = None


@pytest.mark.asyncio
async def test_process_game_logic_unknown():
    """Test unknown command returns generated AI response or default"""
    mock_user_svc = AsyncMock()
    container._user_service = mock_user_svc

    with (
        patch("application.services.rival_service.rival_service") as mock_rival_svc,
        patch("app.main.AsyncSessionLocal") as mock_session_cls,
    ):
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        mock_db_result = MagicMock()
        mock_db_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_db_result
        
        mock_user = MagicMock(is_hollowed=False, hp_status="HEALTHY", level=1)
        mock_user_svc.get_or_create_user.return_value = mock_user
        mock_user_svc.get_user = AsyncMock(return_value=mock_user)
        mock_rival_svc.process_encounter = AsyncMock(return_value="")
        
        mock_rival = MagicMock(level=1)
        mock_rival_svc.get_rival = AsyncMock(return_value=mock_rival)

        # Currently, if unknown, the new AI Persona replies with narrative.
        result = await process_game_logic("test_user_id", "unknown_command_xyz")

        # Check if it returned a response (not crash)
        assert result.text is not None
        assert any(k in result.text for k in ["無法處理", "未知", "戰略", "警告", "偵測", "無效", "訊號", "丟失", "手動"])


    container._user_service = None
