import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.user import User
from app.models.gamification import BossStatus
from app.services.boss_service import boss_service

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with TestSession() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_boss_spawn_and_damage(db_session):
    user_id = "hero1"

    # 1. Spawn Boss
    msg = await boss_service.spawn_boss(db_session, user_id)
    assert "首領現身" in msg

    boss = await boss_service.get_active_boss(db_session, user_id)
    assert boss is not None
    assert boss.status == BossStatus.ACTIVE
    assert boss.hp == 1000

    # 2. Deal Damage
    msg = await boss_service.deal_damage(db_session, user_id, 100)
    assert "造成 100 傷害" in msg

    await db_session.refresh(boss)
    assert boss.hp == 900

    # 3. Kill Boss
    msg = await boss_service.deal_damage(db_session, user_id, 900)
    assert "擊敗" in msg

    await db_session.refresh(boss)
    assert boss.hp == 0
    assert boss.status == BossStatus.DEFEATED


@pytest.mark.asyncio
async def test_boss_rewards(db_session):
    # Setup User
    user = User(id="hero2", gold=0)
    db_session.add(user)
    await db_session.commit()

    # Spawn Boss
    await boss_service.spawn_boss(db_session, "hero2")

    # Kill (1000 dmg)
    await boss_service.deal_damage(db_session, "hero2", 1000)

    # Check Rewards
    await db_session.refresh(user)
    assert user.gold == 500
