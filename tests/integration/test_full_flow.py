from fastapi.testclient import TestClient
import pytest
from unittest.mock import AsyncMock, patch
import os

# FORCE SQLITE BEFORE IMPORTING APP
os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite+aiosqlite:///./test_e2e.db"
os.environ["TESTING"] = "1"

from app.main import app
from app.core.container import container
# from application.services.graph_service import graph_service
from application.services.vector_service import vector_service

# Setup Test Client
client = TestClient(app)


@pytest.fixture(scope="module")
def setup_databases(tmp_path_factory):
    test_root = tmp_path_factory.mktemp("e2e_data")
    chroma_path = test_root / "chroma"
    kuzu_path = test_root / "kuzu" / "graph.db"

    from adapters.persistence.kuzu.adapter import KuzuAdapter
    from adapters.persistence.chroma.adapter import ChromaAdapter

    # Monkeypatch global services with Test DBs - VIA CONTAINER
    # graph_service._adapter = KuzuAdapter(db_path=str(kuzu_path))
    container.graph_service.adapter = KuzuAdapter(db_path=str(kuzu_path))
    vector_service.adapter = ChromaAdapter(collection_name="test_e2e_memories", persist_path=str(chroma_path))

    # Initialize SQL DB Schema
    from app.core.database import engine
    from app.models.base import Base
    import asyncio

    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Run DB Init in a new loop to avoid conflict if any
    # Since this fixture is module scope, it runs once.
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(init_db())

    yield

    # Cleanup?
    # loop.close() # Pytest might manage loops


@pytest.mark.skip(reason="Integration test hangs in CI due to event loop/DB conflicts - run manually")
def test_full_pipeline_ha_event(setup_databases):
    # Mock the Brain properly
    # Note: mocking an async method on a sync call path (via TestClient) works if the app awaits it.

    with patch("application.services.brain_service.brain_service.think", new_callable=AsyncMock) as mock_think:
        mock_think.return_value = """
        {
            "narrative": "Viper notices you.",
            "actions": [
                {"type": "MODIFY_HP", "amount": -1, "reason": "Test Damage"}
            ]
        }
        """

        payload = {"event_type": "screen_on", "state": "on", "attributes": {"source": "test_device"}}

        response = client.post("/api/nerves/perceive", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Debug output if failed
        assert data["status"] == "processed", f"Pipeline Failed: {data.get('message')}"
