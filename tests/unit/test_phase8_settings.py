import pytest
import pytest_asyncio
import sys
from unittest.mock import MagicMock, AsyncMock

# --- MOCK KUZU BEFORE IMPORTS ---
mock_kuzu_mod = MagicMock()
sys.modules["kuzu"] = mock_kuzu_mod
mock_adapter_mod = MagicMock()
sys.modules["adapters.persistence.kuzu.adapter"] = mock_adapter_mod
# --------------------------------



from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.user import User
from app.core.container import container
from application.services.flex_renderer import flex_renderer


# Setup in-memory DB for test
@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def mock_kuzu():
    # Setup Mocks
    mock_kuzu_instance = MagicMock()
    mock_kuzu_instance.query_recent_context = AsyncMock(return_value=[])
    mock_kuzu_instance.record_user_event = AsyncMock()
    
    # Patch ContextService
    from application.services.context_service import context_service
    original_kuzu = context_service.kuzu
    context_service.kuzu = mock_kuzu_instance
    
    yield mock_kuzu_instance
    
    # Teardown
    context_service.kuzu = original_kuzu


@pytest.mark.asyncio
async def test_settings_flow(db_session, mock_kuzu):
    user_id = "test_user_settings"

    # 0. Setup User
    user = User(id=user_id, name="Hero")
    db_session.add(user)
    await db_session.commit()

    # 1. Get Defaults
    settings = await container.user_service.get_settings(db_session, user_id)
    assert settings["theme"] == "cyberpunk"
    assert settings["notifications"] is True

    # 2. Update Setting
    updated = await container.user_service.update_setting(db_session, user_id, "notifications", False)
    assert updated["notifications"] is False

    # Verify Persistence
    await db_session.refresh(user)
    assert user.settings["notifications"] is False

    # 3. Update Theme
    updated = await container.user_service.update_setting(db_session, user_id, "theme", "classic")
    assert updated["theme"] == "classic"

    # 4. Render Profile (Smoke Test)
    try:
        flex = flex_renderer.render_profile(user)
        assert flex is not None
        assert "用戶設定" in str(flex)
    except Exception as e:
        pytest.fail(f"Render Profile failed: {e}")
