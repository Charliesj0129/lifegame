from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class VectorPort(ABC):
    @abstractmethod
    async def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """Embed and store texts with metadata."""
        pass

    @abstractmethod
    async def similarity_search(self, query: str, k: int = 5) -> List[str]:
        """Return most similar texts."""
        pass

    @abstractmethod
    async def search_with_scores(self, query: str, k: int = 5) -> List[tuple[str, float]]:
        """Return texts with similarity scores."""
        pass
