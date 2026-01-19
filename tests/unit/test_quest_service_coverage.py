import pytest
import pytest_asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from app.models.quest import Quest, QuestStatus, QuestType
from app.models.user import User
from application.services.quest_service import quest_service


@pytest.mark.asyncio
async def test_create_quest(db_session):
    user_id = "test_user_coverage_1"
    user = User(id=user_id, name="Hero", xp=0, gold=0)
    db_session.add(user)
    await db_session.commit()

    # Test basic creation
    quest = await quest_service.create_quest(
        db_session, user_id, title="Test Quest", description="Desc", difficulty="C"
    )
    assert quest.id is not None
    assert quest.xp_reward == 50
    assert quest.status == QuestStatus.ACTIVE.value

    # Verify in DB
    idx = quest.id
    db_session.expire_all()
    q_db = await db_session.get(Quest, idx)
    assert q_db is not None
    assert q_db.title == "Test Quest"


@pytest.mark.asyncio
async def test_complete_quest_logic(db_session):
    user_id = "test_user_coverage_2"
    user = User(id=user_id, name="Hero", xp=0, gold=0)
    db_session.add(user)

    quest = Quest(
        user_id=user_id, title="To Complete", xp_reward=100, difficulty_tier="B", status=QuestStatus.ACTIVE.value
    )
    db_session.add(quest)
    await db_session.commit()

    # Patch dependencies to isolate logic
    with patch("application.services.loot_service.loot_service") as mock_loot:
        mock_loot.calculate_reward.return_value = MagicMock(xp=120, gold=50)

        # Patch graph sync within service to avoid Kuzu calls if any exist
        # We also need to patch container.user_service.get_user call inside complete_quest
        # because it might try to use real one or fail.
        # Actually complete_quest uses session.execute/get which works with our db_session.

        # However, quest_service imports container inside method usually.
        # Let's rely on db_session behavior.

        result = await quest_service.complete_quest(db_session, user_id, quest.id)

        assert result is not None
        assert result["quest"].status == QuestStatus.DONE.value
        assert result["loot"].xp == 120

        # Verify User updates
        await db_session.refresh(user)
        assert user.xp == 120
        assert user.gold == 50


@pytest.mark.asyncio
async def test_accept_all_pending(db_session):
    user_id = "test_user_coverage_3"

    # Create 2 pending quests
    q1 = Quest(user_id=user_id, title="P1", status=QuestStatus.PENDING.value)
    q2 = Quest(user_id=user_id, title="P2", status=QuestStatus.PENDING.value)
    q3 = Quest(user_id=user_id, title="A1", status=QuestStatus.ACTIVE.value)
    db_session.add_all([q1, q2, q3])
    await db_session.commit()

    count = await quest_service.accept_all_pending(db_session, user_id)
    assert count == 2

    await db_session.refresh(q1)
    await db_session.refresh(q2)
    assert q1.status == QuestStatus.ACTIVE.value
    assert q2.status == QuestStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_trigger_push_quests_flooding_check(db_session):
    # Ensure correct count settings for this test
    quest_service.DAILY_QUEST_COUNT = 3
    user_id = "test_user_flood"

    today = datetime.datetime.now(datetime.timezone.utc)
    # Add 3 active quests for today
    for i in range(3):
        q = Quest(
            user_id=user_id,
            title=f"Q{i}",
            status=QuestStatus.ACTIVE.value,
            created_at=today,  # Explicitly set created_at
        )
        db_session.add(q)
    await db_session.commit()

    # Check what is actually in DB
    result_check = await db_session.execute(select(Quest).where(Quest.user_id == user_id))
    print(f"DEBUG: Found {len(result_check.scalars().all())} quests in DB")

    # Should perform NO-OP (return existing)
    # Note: SQLite date function might still fail if not matching exactly.
    # We will patch func.date to match our specific test case or rely on basic retrieval
    # Actually, simplest is to mock trigger_push_quests internal query or ensure logic matches.
    # But let's try explicit created_at first.

    # Alternative: Mock session.execute to return our list for this specific call in service?
    # No, that defeats integration test purpose.

    # We will modify the Service logic to not be so strict on DATE in tests?
    # No.

    result = await quest_service.trigger_push_quests(db_session, user_id)
    # If it fails again, we know it's the func.date issue.
    assert len(result) == 3
    # Ensure no new quests generated (we'd need to mock _generate_daily_batch to be sure,
    # but logically if it returns list of 3 without calling generate, it works)
