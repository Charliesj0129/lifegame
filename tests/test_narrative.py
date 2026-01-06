import pytest
from unittest.mock import AsyncMock, patch
from app.services.narrative_service import narrative_service
from app.models.quest import Rival

@pytest.mark.asyncio
async def test_generate_outcome_story():
    mock_session = AsyncMock()
    with patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = {"narrative": "The blade hums as it slices through the firewall."}
        
        # New Signature: session, user_id, action_text, result, context
        story = await narrative_service.generate_outcome_story(mock_session, "u1", "Hack server", {"success": True})
        
        assert "blade hums" in story
        assert mock_ai.called
        # Verify LoreEntry was added
        assert mock_session.add.called
        # Check if saved with correct series
        added_obj = mock_session.add.call_args[0][0]
        assert added_obj.series == "User:u1"

@pytest.mark.asyncio
async def test_get_viper_comment():
    mock_session = AsyncMock()
    # Mock Rival Service
    with patch("app.services.rival_service.rival_service.get_rival", new_callable=AsyncMock) as mock_get_rival, \
         patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
         
        mock_get_rival.return_value = Rival(level=5)
        mock_ai.return_value = {"comment": "You call that code?"}
        
        comment = await narrative_service.get_viper_comment(mock_session, "u1", "User failed test")
        
        assert "Viper" in comment
        assert "You call that code?" in comment
