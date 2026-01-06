import datetime
import pytest
from sqlalchemy import select
from app.models.user import User
from app.models.dda import HabitState, DailyOutcome, CompletionLog
from app.services.dda_service import dda_service


@pytest.mark.asyncio
async def test_dda_missed_days_reduce_tier(db_session):
    user_id = "u_dda_missed"
    db_session.add(User(id=user_id, name="Tester"))
    await db_session.commit()

    today = datetime.date.today()
    state = HabitState(
        user_id=user_id,
        habit_tag="體力",
        tier="T2",
        ema_p=0.4,
        last_zone="RED",
        zone_streak_days=1,
        last_outcome_date=today - datetime.timedelta(days=3),
    )
    db_session.add(state)
    await db_session.commit()

    updated = await dda_service.apply_missed_days(db_session, user_id, "體力")
    assert updated.tier == "T1"


@pytest.mark.asyncio
async def test_dda_record_completion_creates_logs(db_session):
    user_id = "u_dda_complete"
    db_session.add(User(id=user_id, name="Tester"))
    await db_session.commit()

    await dda_service.record_completion(
        db_session,
        user_id=user_id,
        habit_tag="體力",
        tier_used="T1",
        source="quest",
        duration_minutes=10,
    )

    outcome_stmt = select(DailyOutcome).where(
        DailyOutcome.user_id == user_id,
        DailyOutcome.habit_tag == "體力",
        DailyOutcome.is_global.is_(False),
    )
    outcome = (await db_session.execute(outcome_stmt)).scalars().first()
    assert outcome is not None
    assert outcome.done is True

    global_stmt = select(DailyOutcome).where(
        DailyOutcome.user_id == user_id,
        DailyOutcome.is_global.is_(True),
    )
    global_outcome = (await db_session.execute(global_stmt)).scalars().first()
    assert global_outcome is not None
    assert global_outcome.done is True

    log_stmt = select(CompletionLog).where(CompletionLog.user_id == user_id)
    completion_log = (await db_session.execute(log_stmt)).scalars().first()
    assert completion_log is not None
    assert completion_log.tier_used == "T1"
