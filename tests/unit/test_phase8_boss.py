import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.user import User
from app.models.gamification import Boss, BossStatus
from application.services.boss_service import boss_service


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
async def test_boss_flow(db_session):
    user_id = "test_user_boss"

    # 0. Setup User
    user = User(id=user_id, name="Hero", gold=0)
    db_session.add(user)
    await db_session.commit()

    # 1. No Active Boss Initially
    boss = await boss_service.get_active_boss(db_session, user_id)
    assert boss is None

    # 2. Spawn Boss
    msg = await boss_service.spawn_boss(db_session, user_id)
    assert "首領現身" in msg

    boss = await boss_service.get_active_boss(db_session, user_id)
    assert boss is not None
    assert boss.status == BossStatus.ACTIVE
    assert boss.hp == 1000

    # 3. Deal Damage (Partial)
    damage = 500
    msg = await boss_service.deal_damage(db_session, user_id, damage)
    assert "造成 500 傷害" in msg

    await db_session.refresh(boss)
    assert boss.hp == 500
    assert boss.status == BossStatus.ACTIVE

    # 4. Kill Boss (Remaining 500)
    msg = await boss_service.deal_damage(db_session, user_id, 500)
    assert "擊敗" in msg

    await db_session.refresh(boss)
    assert boss.hp == 0
    assert boss.status == BossStatus.DEFEATED

    # Verify Reward
    await db_session.refresh(user)
    assert user.gold == 500
