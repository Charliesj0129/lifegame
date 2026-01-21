from abc import ABC, abstractmethod
from typing import Any, List, Protocol

from domain.events.game_event import GameEvent


class NotificationPort(ABC):
    """
    Output Port: Sends messages back to the user/world.
    Implementations: LineBotAdapter, ConsoleAdapter, HAPushAdapter
    """

    @abstractmethod
    async def send_text(self, user_id: str, text: str):
        pass

    @abstractmethod
    async def send_image(self, user_id: str, image_url: str):
        pass


class PerceptionPort(ABC):
    """
    Input Port: Receives events from the world.
    (Usually implemented by API Routers calling into Application Layer)
    """

    @abstractmethod
    async def normalize_event(self, raw_payload: Any) -> GameEvent:
        pass


class StoragePort(ABC):
    """
    Persistence Port: Saves state.
    Implementations: PostgresAdapter, SqliteAdapter
    """

    # This is a high-level example; likely will use Repository Pattern per Entity
    pass
