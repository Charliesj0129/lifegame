from adapters.persistence.chroma.adapter import ChromaAdapter
from typing import Any
import logging

logger = logging.getLogger(__name__)


class VectorService:
    def __init__(self):
        # Use Adapter instead of direct Client
        self.adapter = ChromaAdapter(collection_name="memories")

    async def add_memory(self, text: str, metadata: dict[str, Any] | None = None):
        """
        Stores a memory into the vector database.
        """
        try:
            # Adapter expects lists
            await self.adapter.add_texts([text], [metadata or {}])
            logger.info(f"Memory stored: {text[:50]}...")
        except Exception as e:
            logger.error(f"Vector Store Error: {e}")

    async def search_memories(self, query: str, n_results: int = 3):
        """
        Retrieves relevant memories based on semantic similarity.
        """
        try:
            # Adapter returns list of strings
            results = await self.adapter.similarity_search(query, k=n_results)
            return results
        except Exception as e:
            logger.error(f"Vector Retrieval Error: {e}")
            return []


vector_service = VectorService()
