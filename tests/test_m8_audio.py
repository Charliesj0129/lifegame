import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from linebot.v3.messaging import AudioMessage, TextMessage, FlexMessage

class TestM8Audio(unittest.IsolatedAsyncioTestCase):
    async def test_webhook_levelup_audio(self):
        """Verify webhook sends audio on level up."""
        from app.api.webhook import handle_message
        
        # Mock Event
        mock_event = MagicMock()
        mock_event.message.text = "Gym"
        mock_event.source.user_id = "U_AUDIO_TEST"
        mock_event.reply_token = "R_TOKEN"

        # Mock API
        mock_api = MagicMock()
        mock_api.show_loading_animation = AsyncMock()
        mock_api.reply_message = AsyncMock()
        
        # Mock Process Result (Level Up = True)
        mock_result = MagicMock()
        mock_result.leveled_up = True
        mock_result.text = "Action Logged"

        # Mock Deps
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.api.webhook.get_messaging_api", return_value=mock_api), \
             patch("app.services.ai_service.ai_router.router", new_callable=AsyncMock) as mock_router, \
             patch("app.api.webhook.audio_service.get_level_up_audio") as mock_audio_svc, \
             patch("app.core.database.AsyncSessionLocal", return_value=mock_ctx), \
             patch("app.api.webhook.user_service.get_or_create_user", new_callable=AsyncMock), \
             patch("app.services.rival_service.RivalService.process_encounter", new_callable=AsyncMock) as mock_rival_encounter:
             
             mock_rival_encounter.return_value = None
             mock_router.return_value = (TextMessage(text="Flex"), "log_action", {"leveled_up": True})

             # Mock Audio Return
             mock_audio_msg = AudioMessage(original_content_url="https://audio", duration=1000)
             mock_audio_svc.return_value = mock_audio_msg
             
             await handle_message(mock_event)
             
             # Verify Reply called with List[Message]
             mock_api.reply_message.assert_called_once()
             call_args = mock_api.reply_message.call_args[0][0] # ReplyMessageRequest
             messages = call_args.messages
             
             self.assertEqual(len(messages), 2, "Should send Text + Audio")
             self.assertIsInstance(messages[1], AudioMessage, "Second message should be Audio")

    async def test_briefing_audio(self):
        """Verify daily briefing includes audio."""
        from app.services.daily_briefing_service import daily_briefing
        
        mock_user = MagicMock(id="U_AUDIO", level=5, xp=100)
        # Mock Rival is handled by the patch below
        mock_rival = MagicMock(level=6, xp=200)
        
        # Mock Deps
        with patch("app.services.daily_briefing_service.get_messaging_api") as mock_get_api, \
             patch("app.services.daily_briefing_service.AsyncSessionLocal") as mock_db, \
             patch("app.services.daily_briefing_service.rival_service.advance_daily_briefing", new_callable=AsyncMock) as mock_update_rival:
             
             mock_update_rival.return_value = mock_rival
             
             mock_api = MagicMock()
             mock_api.push_message = AsyncMock()
             mock_get_api.return_value = mock_api
             
             # Mock DB side effects: User, Quests (Rival is skipped via patch)
             mock_session = MagicMock()
             mock_session.execute = AsyncMock(side_effect=[
                 MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_user)))), # User
                 MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))) # Quests
             ])
             
             ctx = MagicMock()
             ctx.__aenter__ = AsyncMock(return_value=mock_session)
             ctx.__aexit__ = AsyncMock()
             
             mock_db.return_value = ctx
             
             await daily_briefing.process_daily_briefing("U_AUDIO")
             
             mock_api.push_message.assert_called_once()
             call_args = mock_api.push_message.call_args[0][0]
             messages = call_args.messages
             
             self.assertEqual(len(messages), 2, "Should send Audio + Flex")
             self.assertIsInstance(messages[0], AudioMessage, "First message should be Audio")

if __name__ == "__main__":
    unittest.main()
