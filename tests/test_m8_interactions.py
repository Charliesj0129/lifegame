import asyncio
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.daily_briefing_service import daily_briefing
from app.api.webhook import handle_postback
from linebot.v3.webhooks import PostbackEvent, UserSource
from linebot.v3.messaging import FlexMessage


class TestM8Interactions(unittest.TestCase):
    def test_quick_reply_structure(self):
        print("\n--- Testing Quick Reply Generation ---")
        # Mock User/Rival
        user = MagicMock(id="U_TEST", level=5, xp=100)
        rival = MagicMock(level=6, xp=200)
        quests = []

        # Generate Flex
        flex = daily_briefing._create_briefing_flex(user, rival, quests)

        # Check Quick Reply
        assert flex.quick_reply is not None
        items = flex.quick_reply.items
        print(f"Quick Reply Items: {len(items)}")
        assert len(items) == 3

        # Check Actions
        actions = [item.action for item in items]
        labels = [a.label for a in actions]
        datas = [a.data for a in actions]

        print(f"Labels: {labels}")
        print(f"Data: {datas}")

        assert "重新生成" in labels[0] or "Reroll" in labels[0]  # Support Chinese
        assert "action=reroll_quests" in datas
        print("✅ Quick Reply Structure Verified.")

    def test_postback_handling(self):
        print("\n--- Testing Postback Handler ---")
        # Mock Event
        event = MagicMock(spec=PostbackEvent)
        event.source = MagicMock(spec=UserSource)
        event.source.user_id = "U_TEST_POSTBACK"
        event.reply_token = "R_TOKEN"

        # Explicit Postback object
        event.postback = MagicMock()
        event.postback.data = "action=reroll_quests"

        # Mock API
        mock_api = MagicMock()
        mock_api.reply_message = AsyncMock()

        # Run Handler
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        flex_stub = MagicMock(spec=FlexMessage)
        with (
            patch("app.api.webhook.get_messaging_api", return_value=mock_api),
            patch("app.core.database.AsyncSessionLocal", return_value=mock_ctx),
            patch(
                "app.api.webhook.quest_service.reroll_quests", new_callable=AsyncMock
            ) as mock_reroll,
            patch(
                "app.api.webhook.flex_renderer.render_quest_list",
                return_value=flex_stub,
            ) as mock_render,
        ):
            mock_reroll.return_value = []
            # We need to run async function
            loop = asyncio.new_event_loop()
            loop.run_until_complete(handle_postback(event))
            loop.close()

            # Verify Reply
            mock_api.reply_message.assert_called_once()
            args = mock_api.reply_message.call_args[0][0]  # ReplyMessageRequest
            mock_render.assert_called_once()
            assert len(args.messages) == 1
            print("Response: FlexMessage")
            print("✅ Postback 'reroll' handled.")

    def test_postback_equip(self):
        print("\n--- Testing Postback Equip ---")
        event = MagicMock(spec=PostbackEvent)
        event.source = MagicMock(spec=UserSource)
        event.source.user_id = "U_TEST_EQUIP"
        event.reply_token = "R_TOKEN_2"

        event.postback = MagicMock()
        event.postback.data = "action=equip&item_id=EXCALIBUR"

        mock_api = MagicMock()
        mock_api.reply_message = AsyncMock()

        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.api.webhook.get_messaging_api", return_value=mock_api),
            patch("app.core.database.AsyncSessionLocal", return_value=mock_ctx),
        ):
            loop = asyncio.new_event_loop()
            loop.run_until_complete(handle_postback(event))
            loop.close()

            mock_api.reply_message.assert_called_once()
            args = mock_api.reply_message.call_args[0][0]
            reply_text = args.messages[0].text
            print(f"Response: {reply_text}")
            assert (
                "裝備" in reply_text or "Equipping" in reply_text
            )  # Chinese: 裝備道具
            print("✅ Postback 'equip' handled.")


if __name__ == "__main__":
    unittest.main()
