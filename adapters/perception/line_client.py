import logging
from typing import Any, List, Optional, Union

from linebot.v3.messaging import (
    ImageMessage,
    MessagingApi,
    PushMessageRequest,
    QuickReply,
    QuickReplyItem,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.messaging import (
    PostbackAction as LinePostbackAction,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from application.services.line_bot import get_messaging_api  # Legacy helper for now
from domain.models.game_result import GameResult

logger = logging.getLogger(__name__)


class LineClient:
    """
    Adapter for LINE Messaging API.
    Implements MessagingPort.
    """

    def __init__(self):
        # We rely on the global get_messaging_api for now to avoid refactoring config loading yet
        pass

    async def send_reply(self, token: str, result: GameResult, user_id: str | None = None) -> bool:
        """
        Sends a GameResult as a LINE format reply.
        If replying fails (e.g. invalid token), it does NOT fallback internally to reply again.
        It raises exception so the caller can switch to Push.
        """
        try:
            api = get_messaging_api()
            if not api:
                logger.warning("Line Messaging API not initialized.")
                return False

            messages = self._to_line_messages(result)
            # LOGGING: payload check
            try:
                msg_summary = [str(m) for m in messages]
                logger.info(f"Sending Reply to {token[:10]}...: {len(messages)} msgs. Type: {msg_summary}")
            except Exception:
                pass

            await api.reply_message(ReplyMessageRequest(reply_token=token, messages=messages))
            logger.info("Reply Sent Successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to send LINE reply: {e}", exc_info=True)
            raise e

    async def send_push(self, user_id: str, result: GameResult) -> bool:
        """
        Sends a GameResult as a LINE Push Message (Fallback).
        Includes Safe Mode (Text Only) if Rich Push fails.
        """
        api = get_messaging_api()
        if not api:
            return False

        try:
            # 1. Try Rich Push
            messages = self._to_line_messages(result)
            await api.push_message(PushMessageRequest(to=user_id, messages=messages))
            return True
        except Exception as e:
            logger.error(f"Failed to send LINE push (Rich): {e}. Attempting Text Fallback.")
            try:
                # 2. Try Text Push (Safe Mode)
                if result.text:
                    from linebot.v3.messaging import TextMessage

                    fallback_msg = [TextMessage(text=f"{result.text}\n\n(⚠️ Display Error: Rich content failed)")]
                    await api.push_message(PushMessageRequest(to=user_id, messages=fallback_msg))
                    return True
                return False
            except Exception as e2:
                logger.error(f"Text Fallback Push also failed: {e2}")
                return False

    def _to_line_messages(self, result: GameResult) -> List[Any]:
        """
        Converts a single GameResult into a list of LINE messages.
        Handles formatting, Persona injection, and metadata extras.
        """
        from linebot.v3.messaging import FlexMessage

        messages = []
        meta = result.metadata or {}

        # 1. Pre-Message (e.g. Rival Taunt separate from Image)
        if meta.get("pre_text"):
            # TODO: Handle pre_sender persona
            messages.append(TextMessage(text=meta["pre_text"]))

        # 2. Main Content
        if meta.get("flex_message"):
            # Direct Flex Object passing (singular)
            messages.append(meta["flex_message"])

        # 2b. Tool-generated Flex Messages (list) - Fix #1
        if meta.get("flex_messages"):
            for flex_msg in meta["flex_messages"]:
                messages.append(flex_msg)

        elif result.image_url:
            msg = ImageMessage(
                original_content_url=result.image_url,
                preview_image_url=result.image_url,
            )
            messages.append(msg)

        elif result.text and not meta.get("flex_message"):
            # Only verify text if no Flex (Flex usually overrides text)
            # But if both exist, maybe send both?
            # Legacy logic: if Flex, text is ignored or separate.
            # Let's send text if it's not "Flex Message" placeholder
            if result.text != "Flex Message":
                messages.append(TextMessage(text=result.text))

        # 3. Quick Replies (Attach to LAST message) - Fix #5
        if meta.get("quick_reply") and messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "quick_reply"):
                last_msg.quick_reply = meta["quick_reply"]

        # 4. Audio Message (Fanfare)
        if meta.get("audio_message"):
            messages.append(meta["audio_message"])

        # 5. Legacy List (from Postback)
        if meta.get("legacy_messages"):
            # These are already Line Message Objects
            messages.extend(meta["legacy_messages"])

        # Inject Sender (Persona) - ONLY for TextMessage for now
        sender_persona = meta.get("sender")
        if sender_persona:
            # Need to get sender object from persona_service?
            # LineClient shouldn't depend on persona_service directly...
            # But we need the icon/name.
            # Passed as object? GameLoop passed 'persona_service.SYSTEM' which is a Dict/Obj?
            # Let's import persona_service here? Coupling risk.
            # Or assume it was resolved to Name/Icon in GameResult?
            # For Phase 1, import service or helper.
            from application.services.persona_service import persona_service

            sender_obj = persona_service.get_sender_object(sender_persona)

            for m in messages:
                if isinstance(m, TextMessage):
                    m.sender = sender_obj

        return messages


line_client = LineClient()
