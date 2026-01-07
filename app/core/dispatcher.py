from typing import Callable, Any, Awaitable
import logging
from linebot.v3.messaging import TextMessage

logger = logging.getLogger(__name__)


class CommandDispatcher:
    """
    Central Command Dispatcher (Command Bus Pattern).
    Decouples 'Intent Recognition' from 'Action Execution'.
    """

    def __init__(self):
        # List of (matcher_func, handler_func)
        # matcher_func: (text: str) -> bool
        # handler_func: (session, user_id, text) -> (response_message, intent_tool_name)
        self._strategies = []
        self._default_strategies = []  # Priority Low (e.g. AI Fallback)

    def register(
        self, matcher: Callable[[str], bool], handler: Callable[..., Awaitable[Any]]
    ):
        """Register a high-priority exact or regex matcher."""
        self._strategies.append((matcher, handler))

    def register_default(self, handler: Callable[..., Awaitable[Any]]):
        """Register a catch-all handler (e.g. AI Router/Verification)."""
        self._default_strategies.append(handler)

    async def dispatch(self, session, user_id: str, text: str):
        text.strip().lower()

        # 1. High Priority Strategies (Fast Exact Matches)
        for matcher, handler in self._strategies:
            if matcher(
                text
            ):  # Pass raw text usually, or normalized? Let matcher decide.
                logger.info(f"Dispatcher: Matched handler {handler.__name__}")
                return await handler(session, user_id, text)

        # 2. Defaults (AI Router, Verification)
        for handler in self._default_strategies:
            res = await handler(session, user_id, text)
            if res:  # If handler returns something legitimate (not None)
                return res
        
        return TextMessage(text="⚠️ 無法處理此請求。"), "unknown", {}


# Singleton Instance
dispatcher = CommandDispatcher()
