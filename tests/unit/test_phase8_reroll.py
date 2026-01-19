import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.base import Base
from app.models.user import User
from app.models.quest import Quest, QuestStatus
from application.services.quest_service import quest_service


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
async def test_reroll_flow(db_session):
    user_id = "test_user_reroll"

    # 0. Setup User with Gold
    user = User(id=user_id, name="Hero", gold=200)
    db_session.add(user)
    await db_session.commit()

    # 1. Create Initial Quests (Simulate daily batch)
    original_count = quest_service.DAILY_QUEST_COUNT
    quest_service.DAILY_QUEST_COUNT = 1  # Simple test
    try:
        quests = await quest_service.trigger_push_quests(db_session, user_id, "Morning")
        assert len(quests) > 0
        old_qid = quests[0].id

        # 2. Reroll Success
        new_quests, viper = await quest_service.reroll_quests(db_session, user_id, cost=100)
        assert new_quests is not None
        assert len(new_quests) > 0
        assert new_quests[0].id != old_qid

        # Verify Gold Deduction
        await db_session.refresh(user)
        assert user.gold == 100  # 200 - 100

    finally:
        quest_service.DAILY_QUEST_COUNT = original_count

    # 3. Reroll Fail (Insufficient Funds)
    # User has 100, reroll costs 100 -> OK.
    # Reroll again -> 0 -> OK.
    # Reroll again -> -100 -> Check fail logic

    await quest_service.reroll_quests(db_session, user_id, cost=100)  # Gold becomes 0
    await db_session.refresh(user)
    assert user.gold == 0

    # Attempt Reroll with 0 Gold
    new_quests_fail, msg = await quest_service.reroll_quests(db_session, user_id, cost=100)
    assert new_quests_fail is None
    assert "金幣不足" in msg

    await db_session.refresh(user)
    assert user.gold == 0  # Unchanged
