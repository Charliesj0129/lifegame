import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.user import User
from legacy.services.user_service import user_service
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
async def test_settings_flow(db_session):
    user_id = "test_user_settings"

    # 0. Setup User
    user = User(id=user_id, name="Hero")
    db_session.add(user)
    await db_session.commit()

    # 1. Get Defaults
    settings = await user_service.get_settings(db_session, user_id)
    assert settings["theme"] == "cyberpunk"
    assert settings["notifications"] is True

    # 2. Update Setting
    updated = await user_service.update_setting(db_session, user_id, "notifications", False)
    assert updated["notifications"] is False

    # Verify Persistence
    await db_session.refresh(user)
    assert user.settings["notifications"] is False

    # 3. Update Theme
    updated = await user_service.update_setting(db_session, user_id, "theme", "classic")
    assert updated["theme"] == "classic"

    # 4. Render Profile (Smoke Test)
    try:
        flex = flex_renderer.render_profile(user)
        assert flex is not None
        assert "用戶設定" in str(flex)
    except Exception as e:
        pytest.fail(f"Render Profile failed: {e}")
