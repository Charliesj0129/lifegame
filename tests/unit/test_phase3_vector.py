import pytest
import os
import shutil
from adapters.persistence.chroma.adapter import ChromaAdapter

# Skip in CI/Mock environment
if os.environ.get("TESTING") == "1":
    pytest.skip("Skipping Phase 3 Vector tests in CI/Mock environment", allow_module_level=True)

TEST_CHROMA_PATH = "./data/test_chroma_db"


@pytest.fixture
def chroma_adapter(tmp_path):
    # Setup
    persist_path = tmp_path / "chroma_db"
    adapter = ChromaAdapter(collection_name="test_memories", persist_path=str(persist_path))
    yield adapter

    # Teardown
    # Chroma keeps open handles sometimes, explicit close if client supports it?
    # New Chroma Client doesn't need explicit close usually but let's be safe.
    # Just rm tree
    # shutil.rmtree(TEST_CHROMA_PATH) # Might fail if file locked, ignore for test


@pytest.mark.asyncio
async def test_chroma_add_and_search(chroma_adapter):
    # Arrange
    texts = ["I love coding", "I hate bugs"]
    metadatas = [{"source": "test"}, {"source": "test"}]

    # Act
    await chroma_adapter.add_texts(texts, metadatas)

    # Assert
    results = await chroma_adapter.similarity_search("coding", k=1)
    assert len(results) == 1
    assert results[0] == "I love coding"


@pytest.mark.asyncio
async def test_chroma_search_with_scores(chroma_adapter):
    await chroma_adapter.add_texts(["apple", "banana"], [{"id": "1"}, {"id": "2"}])

    results = await chroma_adapter.search_with_scores("apple", k=1)
    assert len(results) == 1
    doc, score = results[0]
    assert doc == "apple"
    # Distance should be near 0 for exact match
    assert score < 0.001
