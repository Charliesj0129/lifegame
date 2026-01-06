import pytest
from unittest.mock import AsyncMock, patch
from app.services.verification_service import verification_service, VERDICT_APPROVED, VERDICT_REJECTED

@pytest.mark.asyncio
async def test_verify_text_report():
    with patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {
            "verdict": "APPROVED",
            "reason": "User mentioned running 5km."
        }
        
        result = await verification_service.verify_text_report("I ran 5km today.", "Run 5km")
        
        assert result["verdict"] == VERDICT_APPROVED
        assert "5km" in result["reason"]
        
        args = mock_gen.call_args[0]
        assert "Run 5km" in args[1]
        assert "I ran 5km" in args[1]

@pytest.mark.asyncio
async def test_verify_image_report():
    with patch("app.services.ai_engine.ai_engine.analyze_image", new_callable=AsyncMock) as mock_vision:
        mock_vision.return_value = {
            "verdict": "REJECTED",
            "reason": "Image shows a cat, not a salad.",
            "tags": ["cat", "animal"]
        }
        
        fake_image = b"\x00\x00\x00"
        result = await verification_service.verify_image_report(fake_image, "image/jpeg", "Eat a Salad")
        
        assert result["verdict"] == VERDICT_REJECTED
        assert "cat" in result["tags"]
        
        # Verify call signature
        mock_vision.assert_called_with(fake_image, "image/jpeg", "Eat a Salad")
