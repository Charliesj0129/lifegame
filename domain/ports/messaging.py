from typing import Protocol, Any, Dict, Optional
from domain.models.game_result import GameResult

class MessagingPort(Protocol):
    """
    Interface for sending messages to external platforms (LINE, Discord, etc.)
    """
    async def send_reply(self, token: str, result: GameResult) -> bool:
        """Send a standard GameResult reply."""
        ...

    async def send_push_message(self, user_id: str, messages: list[Any]) -> bool:
        """Send a proactive push message."""
        ...
