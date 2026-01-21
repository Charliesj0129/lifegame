import uuid
from typing import Any, Dict, List, Tuple

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from domain.ports.vector_port import VectorPort


class ChromaAdapter(VectorPort):
    def __init__(self, collection_name: str = "lifgame_memory", persist_path: str = "./data/chroma_db"):
        # Explicitly disable telemetry to prevent PostHog callbacks
        self.client = chromadb.PersistentClient(
            path=persist_path,
            settings=Settings(anonymized_telemetry=False),
        )

        # Use default embedding function for now (SentenceTransformer)
        self.ef = embedding_functions.DefaultEmbeddingFunction()

        self.collection = self.client.get_or_create_collection(name=collection_name, embedding_function=self.ef)

    async def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        if not texts:
            return

        ids = [str(uuid.uuid4()) for _ in texts]
        # Cast metadatas to match Chroma expectations if needed or leave as is if MyPy is just being strict about Dict
        # Chroma expects Mapping[str, str | int | float | bool] roughly
        self.collection.add(documents=texts, metadatas=metadatas, ids=ids)  # type: ignore

    async def similarity_search(self, query: str, k: int = 5) -> List[str]:
        results = self.collection.query(query_texts=[query], n_results=k)
        return results["documents"][0] if results["documents"] else []

    async def search_with_scores(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        results = self.collection.query(query_texts=[query], n_results=k, include=["documents", "distances"])

        docs = results["documents"][0] if results["documents"] else []
        distances = results["distances"][0] if results["distances"] else []

        # Chroma returns distances (lower is better), but usually scores mean higher is better.
        # The interface doesn't strictly specify score metric, but usually consumers expect similarity.
        # For now return raw distance or convert? Let's return raw distance but note it.
        return list(zip(docs, distances))
