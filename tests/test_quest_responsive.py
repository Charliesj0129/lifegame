import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch, MagicMock
from app.services.quest_service import quest_service
from app.services.ai_engine import ai_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import Base
from app.models.quest import Quest

# Setup Test DB
import os
DB_FILE = "./test_quest_responsive.db"
DB_URL = f"sqlite+aiosqlite:///{DB_FILE}"

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def db_session():
    # Setup
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        
    await engine.dispose()
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

async def slow_ai_response(*args, **kwargs):
    """Simulates a slow AI that sleeps for 5 seconds."""
    await asyncio.sleep(5.0)
    return [{"title": "Slow Quest", "desc": "Should not appear", "diff": "A", "xp": 100}]

@pytest.mark.asyncio
async def test_ai_timeout_fallback(db_session):
    """
    Verifies that if AI takes > 3s, the service falls back to templates
    immediately correctly (approx 3s)
    """
    user_id = "test_user_timeout"
    
    # Mock the AI engine's generate_json method
    with patch.object(ai_engine, 'generate_json', side_effect=slow_ai_response):
        start_time = asyncio.get_running_loop().time()
        
        # This calls _generate_daily_batch internally if no quests exist
        quests = await quest_service.get_daily_quests(db_session, user_id)
        
        end_time = asyncio.get_running_loop().time()
        duration = end_time - start_time
        
        # Assertions
        print(f"Quest Gen Duration: {duration:.2f}s")
        
        # 1. Should be faster than the 5s sleep (plus some overhead, say < 3.5s)
        assert duration < 4.0, "Quest generation took too long, timeout failed"
        assert duration >= 3.0, "Timeout didn't wait for approximately 3 seconds" # wait_for waits until timeout
        
        # 2. Check Fallback Content
        assert len(quests) == 3
        # Fallback template #1 title is "System Reboot"
        assert quests[0].title == "System Reboot"
        assert "(Fallback)" in quests[0].description
