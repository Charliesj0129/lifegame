"""
Tests for HP/Hollowed System
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
from app.services.hp_service import hp_service


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session


@pytest.mark.asyncio
async def test_new_user_starts_healthy(db_session):
    """New user should have hp=100, hp_status=HEALTHY."""
    user = User(id="test_hp_new", name="New User")
    db_session.add(user)
    await db_session.commit()

    assert user.hp == 100
    assert user.max_hp == 100
    assert user.hp_status == "HEALTHY"
    assert not user.is_hollowed


@pytest.mark.asyncio
async def test_calculate_daily_drain_no_activity(db_session):
    """User with no activity date should have no drain."""
    user = User(id="test_no_activity", name="No Activity")
    db_session.add(user)
    await db_session.commit()

    drain = await hp_service.calculate_daily_drain(db_session, user)
    assert drain == 0


@pytest.mark.asyncio
async def test_calculate_daily_drain_inactive_days(db_session):
    """2 days inactive should drain 20 HP (10 per day)."""
    user = User(
        id="test_inactive",
        name="Inactive User",
        last_active_date=datetime.now(timezone.utc) - timedelta(days=3),
    )
    db_session.add(user)
    await db_session.commit()

    drain = await hp_service.calculate_daily_drain(db_session, user)
    assert drain == 20  # 2 inactive days * 10 HP


@pytest.mark.asyncio
async def test_apply_hp_change_negative(db_session):
    """HP should decrease and status should update."""
    user = User(id="test_damage", name="Damaged User", hp=50, hp_status="HEALTHY")
    db_session.add(user)
    await db_session.commit()

    user = await hp_service.apply_hp_change(db_session, user, -30, "test")

    assert user.hp == 20
    assert user.hp_status == "CRITICAL"  # Below 30


@pytest.mark.asyncio
async def test_hp_zero_triggers_hollowed(db_session):
    """HP reaching 0 sets is_hollowed=True, hp_status=HOLLOWED."""
    user = User(id="test_hollowed", name="Hollowed User", hp=10, hp_status="CRITICAL")
    db_session.add(user)
    await db_session.commit()

    user = await hp_service.apply_hp_change(db_session, user, -15, "inactivity")

    assert user.hp == 0
    assert user.hp_status == "HOLLOWED"
    assert user.is_hollowed
    assert user.hollowed_at is not None


@pytest.mark.asyncio
async def test_quest_completion_restores_hp(db_session):
    """Completing a quest restores HP based on difficulty."""
    user = User(id="test_restore", name="Restoring User", hp=50, hp_status="HEALTHY")
    db_session.add(user)
    await db_session.commit()

    # Complete a C-tier quest (restores 20 HP)
    user = await hp_service.restore_hp_from_quest(db_session, user, "C")

    assert user.hp == 70


@pytest.mark.asyncio
async def test_hp_capped_at_max(db_session):
    """HP should not exceed max_hp."""
    user = User(
        id="test_cap", name="Capped User", hp=95, max_hp=100, hp_status="HEALTHY"
    )
    db_session.add(user)
    await db_session.commit()

    user = await hp_service.apply_hp_change(db_session, user, 20, "overheal")

    assert user.hp == 100  # Capped at max


@pytest.mark.asyncio
async def test_recovering_status_after_heal(db_session):
    """Hollowed user healing above 0 should become RECOVERING."""
    user = User(
        id="test_recover",
        name="Recovering User",
        hp=0,
        hp_status="HOLLOWED",
        is_hollowed=True,
    )
    db_session.add(user)
    await db_session.commit()

    user = await hp_service.apply_hp_change(db_session, user, 30, "rescue_complete")

    assert user.hp == 30
    assert user.hp_status == "RECOVERING"
    assert not user.is_hollowed


@pytest.mark.asyncio
async def test_get_hp_display(db_session):
    """Get formatted HP display information."""
    user = User(
        id="test_display", name="Display User", hp=75, max_hp=100, hp_status="HEALTHY"
    )
    db_session.add(user)
    await db_session.commit()

    display = await hp_service.get_hp_display(user)

    assert display["hp"] == 75
    assert display["max_hp"] == 100
    assert display["percentage"] == 75
    assert display["status"] == "HEALTHY"
    assert display["emoji"] == "💚"
