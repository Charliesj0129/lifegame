import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from unittest.mock import AsyncMock, MagicMock, patch
# linebot imports might be needed for types if I use them, but purely for patching string paths they might not be strictly needed for *execution* logic of the test unless I instantiate them.
# The test uses TextMessage etc.
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import TextMessage
@pytest.mark.asyncio
async def test_webhook_flow():
    # Mock settings to avoid warnings
    with patch("app.core.config.settings.LINE_CHANNEL_SECRET", "secret"), \
         patch("app.core.config.settings.LINE_CHANNEL_ACCESS_TOKEN", "token"), \
         patch("app.core.config.settings.GOOGLE_API_KEY", "key"):
        
        # Mock Line Handler to not fail on signature
        with patch("app.services.line_bot.AsyncWebhookHandler.handle", new_callable=AsyncMock) as mock_handle:
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/callback", 
                    content="dummy_body", 
                    headers={"X-Line-Signature": "dummy_sig"}
                )
            
            assert response.status_code == 200
            assert response.json() == "OK"
            mock_handle.assert_awaited_once()

@pytest.mark.asyncio
async def test_ai_integration():
    # Verify AI Engine calls Gemini
    with patch("google.generativeai.GenerativeModel.generate_content_async", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value.text = '{"text": "Hero, you gained +5 STR!"}'
        
        from app.services.ai_engine import ai_engine
        # Force init since we might not have env vars set in real env
        # Update for new provider logic
        ai_engine.provider = "google"
        ai_engine.model = MagicMock()
        ai_engine.model.generate_content_async = mock_gen
        
        response = await ai_engine.generate_json("sys", "user")
        
        assert response == {"text": "Hero, you gained +5 STR!"}
        mock_gen.assert_awaited_once()
