import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.user import User
from legacy.services.help_service import help_service
from legacy.services.flex_renderer import flex_renderer


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
async def test_help_logic(db_session):
    user_id = "test_user_help"

    # 0. Setup Healthy User
    user = User(id=user_id, name="Hero", hp=100, is_hollowed=False)
    db_session.add(user)
    await db_session.commit()

    # 1. Default Tip (No critical issues)
    tip = await help_service.get_dynamic_help(db_session, user)
    # Could be Explore or Shop, random choice.
    assert "title" in tip
    assert "action_label" in tip

    # 2. Critical Health
    user.hp = 10
    db_session.add(user)
    await db_session.commit()

    tip = await help_service.get_dynamic_help(db_session, user)
    assert "生命危急" in tip["title"]
    assert tip["priority"] == 100

    # 3. Hollowing (Priority 95)
    # If both Low HP (100) and Hollowing (95), HP should win.
    user.is_hollowed = True
    db_session.add(user)
    await db_session.commit()

    tip = await help_service.get_dynamic_help(db_session, user)
    assert "生命危急" in tip["title"]  # still priority 100

    # Heal up, but keep hollowing
    user.hp = 100
    db_session.add(user)
    await db_session.commit()

    tip = await help_service.get_dynamic_help(db_session, user)
    assert "活屍化警告" in tip["title"]  # priority 95

    # 4. Render Smoke Test
    flex = flex_renderer.render_help_card(tip)
    assert "活屍化警告" in str(flex)
