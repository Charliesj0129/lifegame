from abc import ABC, abstractmethod
from typing import Any, Dict

from domain.events.game_event import GameEvent
from domain.models.game_result import GameResult


class PerceptionPort(ABC):
    @abstractmethod
    async def process_event(self, event: GameEvent) -> GameResult:
        """
        Process a normalized GameEvent through the cognitive pipeline
        and return a GameResult (narrative + actions).
        """
        pass
