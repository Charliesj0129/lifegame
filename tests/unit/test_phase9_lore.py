import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from legacy.models.lore import LoreProgress, LoreEntry
from legacy.services.lore_service import lore_service


# Setup in-memory DB for test
@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session


@pytest.mark.asyncio
async def test_lore_unlock_flow(db_session):
    user_id = "u_lore_test"

    # Mock AI
    with patch("legacy.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = {"title": "Chapter Title", "body": "Story content."}

        # 1. Level 1 -> Unlock Chapter 1
        entry = await lore_service.check_lore_unlock(db_session, user_id, 1)
        assert entry is not None
        assert entry.chapter == 1
        assert entry.series == f"User:{user_id}"

        # Verify Progress
        mock_ai.call_count = 1

        # 2. Level 2 -> Low Threshold -> No Unlock (Next unlock at 5)
        entry = await lore_service.check_lore_unlock(db_session, user_id, 2)
        assert entry is None

        # 3. Level 5 -> Unlock Chapter 2
        entry = await lore_service.check_lore_unlock(db_session, user_id, 5)
        assert entry is not None
        assert entry.chapter == 2

        mock_ai.call_count = 2


@pytest.mark.asyncio
async def test_get_user_lore(db_session):
    user_id = "u_lore_read"

    # Seed Data
    e1 = LoreEntry(series=f"User:{user_id}", chapter=1, title="C1", body="B1")
    e2 = LoreEntry(series=f"User:{user_id}", chapter=2, title="C2", body="B2")
    db_session.add_all([e1, e2])
    await db_session.commit()

    lore_list = await lore_service.get_user_lore(db_session, user_id)
    assert len(lore_list) == 2
    assert lore_list[0].title == "C1"
    assert lore_list[1].title == "C2"
