"""
副本系統單元測試
Tests for Phase 9: Dungeon System (Focus Mode)
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import uuid

from app.models.base import Base
from app.models.user import User
from app.models.dungeon import Dungeon, DungeonStage, DungeonStatus, DungeonType, DUNGEON_TEMPLATES
from app.services.dungeon_service import dungeon_service


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session


async def create_test_user(session, user_id: str) -> User:
    """Helper to create a test user"""
    user = User(id=user_id, name=f"Tester_{user_id[:8]}", xp=100)
    session.add(user)
    await session.commit()
    return user


@pytest.mark.asyncio
async def test_dungeon_templates():
    """Verify dungeon templates are properly defined."""
    assert len(DUNGEON_TEMPLATES) == 5
    
    for dtype, template in DUNGEON_TEMPLATES.items():
        assert "name" in template
        assert "duration_minutes" in template
        assert "stages" in template
        assert len(template["stages"]) >= 2


@pytest.mark.asyncio
async def test_open_dungeon(db_session):
    """Test opening a new dungeon."""
    user_id = f"user_{uuid.uuid4()}"
    await create_test_user(db_session, user_id)
    
    dungeon, msg = await dungeon_service.open_dungeon(
        db_session, user_id, "WRITING"
    )
    
    assert dungeon is not None
    assert dungeon.name == "寫作深淵"
    assert dungeon.status == DungeonStatus.ACTIVE.value
    assert dungeon.duration_minutes == 90
    assert "副本已開啟" in msg


@pytest.mark.asyncio
async def test_open_dungeon_already_active(db_session):
    """Test cannot open second dungeon while one is active."""
    user_id = f"user_{uuid.uuid4()}"
    await create_test_user(db_session, user_id)
    
    # Open first dungeon
    await dungeon_service.open_dungeon(db_session, user_id, "WRITING")
    
    # Try to open second
    dungeon2, msg = await dungeon_service.open_dungeon(
        db_session, user_id, "CODING"
    )
    
    assert dungeon2 is None
    assert "已經在副本" in msg


@pytest.mark.asyncio
async def test_get_dungeon_stages(db_session):
    """Test fetching dungeon stages."""
    user_id = f"user_{uuid.uuid4()}"
    await create_test_user(db_session, user_id)
    
    dungeon, _ = await dungeon_service.open_dungeon(
        db_session, user_id, "WRITING"
    )
    
    stages = await dungeon_service.get_dungeon_stages(db_session, dungeon.id)
    
    assert len(stages) == 3  # Writing has 3 stages
    assert stages[0].order == 1
    assert stages[1].order == 2
    assert stages[2].order == 3
    assert all(not s.is_complete for s in stages)


@pytest.mark.asyncio
async def test_complete_stage(db_session):
    """Test completing a dungeon stage."""
    user_id = f"user_{uuid.uuid4()}"
    await create_test_user(db_session, user_id)
    
    # Open dungeon
    dungeon, _ = await dungeon_service.open_dungeon(
        db_session, user_id, "MEDITATION"
    )
    
    # Complete first stage
    success, msg = await dungeon_service.complete_stage(db_session, user_id)
    
    assert success
    assert "完成" in msg
    assert "進度：1/2" in msg


@pytest.mark.asyncio
async def test_complete_all_stages_clears_dungeon(db_session):
    """Test completing all stages clears the dungeon."""
    user_id = f"user_{uuid.uuid4()}"
    await create_test_user(db_session, user_id)
    
    # Open meditation dungeon (2 stages)
    dungeon, _ = await dungeon_service.open_dungeon(
        db_session, user_id, "MEDITATION"
    )
    
    # Complete both stages
    await dungeon_service.complete_stage(db_session, user_id)
    success, msg = await dungeon_service.complete_stage(db_session, user_id)
    
    assert success
    assert "通關" in msg
    
    # Verify dungeon is no longer active
    active = await dungeon_service.get_active_dungeon(db_session, user_id)
    assert active is None


@pytest.mark.asyncio
async def test_abandon_dungeon(db_session):
    """Test abandoning a dungeon."""
    user_id = f"user_{uuid.uuid4()}"
    await create_test_user(db_session, user_id)
    
    # Open dungeon
    await dungeon_service.open_dungeon(db_session, user_id, "WRITING")
    
    # Abandon
    success, msg = await dungeon_service.abandon_dungeon(db_session, user_id)
    
    assert success
    assert "放棄" in msg
    
    # Verify no active dungeon
    active = await dungeon_service.get_active_dungeon(db_session, user_id)
    assert active is None


@pytest.mark.asyncio
async def test_no_active_dungeon(db_session):
    """Test actions when no dungeon is active."""
    user_id = f"user_{uuid.uuid4()}"
    await create_test_user(db_session, user_id)
    
    # Try to complete stage without active dungeon
    success, msg = await dungeon_service.complete_stage(db_session, user_id)
    
    assert not success
    assert "沒有進行中" in msg


@pytest.mark.asyncio
async def test_remaining_time_calculation():
    """Test remaining time calculation."""
    from datetime import timezone
    # Create mock dungeon with deadline 30 minutes from now
    from unittest.mock import MagicMock
    dungeon = MagicMock()
    dungeon.deadline = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    remaining = await dungeon_service.get_remaining_time(dungeon)
    
    # Should be around "29:xx" or "30:xx"
    assert ":" in remaining
    minutes = int(remaining.split(":")[0])
    assert 28 <= minutes <= 31

