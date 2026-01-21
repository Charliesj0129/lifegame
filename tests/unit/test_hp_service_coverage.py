import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.future import select

from app.models.quest import Quest, QuestStatus
from app.models.user import User
from application.services.hp_service import hp_service


@pytest.mark.asyncio
async def test_apply_hp_change_clamping(db_session):
    user_id = "test_user_hp_1"
    user = User(id=user_id, name="Hero", hp=50, max_hp=100)
    db_session.add(user)
    await db_session.commit()

    # Test +100 -> clamped at 100
    updated = await hp_service.apply_hp_change(db_session, user, 100)
    assert updated.hp == 100

    # Test -200 -> clamped at 0
    updated = await hp_service.apply_hp_change(db_session, user, -200)
    assert updated.hp == 0
    assert updated.is_hollowed is True
    assert updated.hp_status == "HOLLOWED"


@pytest.mark.asyncio
async def test_trigger_rescue_protocol(db_session):
    user_id = "test_user_hp_rescue"
    user = User(id=user_id, name="Hero", hp=0, is_hollowed=True, hp_status="HOLLOWED")

    # Create an active quest that should be PAUSED
    q = Quest(user_id=user_id, status=QuestStatus.ACTIVE.value, title="To Pause")
    db_session.add(user)
    db_session.add(q)
    await db_session.commit()

    with patch(
        "application.services.dungeon_service.dungeon_service.start_dungeon", new_callable=AsyncMock
    ) as mock_dungeon:
        mock_dungeon.return_value = {"message": "Rescue started"}

        msg = await hp_service.trigger_rescue_protocol(db_session, user)
        assert "Rescue started" in msg

        # Verify Quest Paused
        await db_session.refresh(q)
        assert q.status == QuestStatus.PAUSED.value

        # Verify dungeon call
        mock_dungeon.assert_called_once()


@pytest.mark.asyncio
async def test_calculate_daily_drain(db_session):
    user_id = "test_user_drain"
    # User inactive for 2 days (today - 2 days ago = 2 days diff -> 1 day drain)
    # Logic: delta_days = (today - last_active).days - 1
    # Logic: delta_days = (today - last_active).days - 1

    last_active = datetime.datetime.now() - datetime.timedelta(days=2)

    user = User(id=user_id, name="Hero", hp=100, last_active_date=last_active)
    db_session.add(user)
    await db_session.commit()

    drain = await hp_service.calculate_daily_drain(db_session, user)
    # Diff = 2 days. 2 - 1 = 1 day logic check.
    # If yesterday was missed, drain applies?
    # Logic: if last_active is day X, today is X+2.
    # Missed X+1. So 1 day missed.
    # Drain = 10 * 1 = 10.

    assert drain == 10

    await db_session.refresh(user)
    assert user.hp == 90


@pytest.mark.asyncio
async def test_restore_by_difficulty(db_session):
    user_id = "test_user_restore"
    user = User(id=user_id, name="Hero", hp=50)
    db_session.add(user)

    delta = await hp_service.restore_by_difficulty(db_session, user, "C")
    assert delta == 20
    assert user.hp == 70
