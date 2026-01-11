import pytest
import shutil
import tempfile
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.main import process_game_logic
import pytest_asyncio

# 1. Integration Setup
# Use a separate temporary directory for KuzuDB and SQLite
@pytest_asyncio.fixture(scope="module")
async def real_env():
    # Setup Paths
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_real.db")
    kuzu_path = os.path.join(temp_dir, "test_kuzu")
    
    # Set Env Vars ensure Adapter picks it up
    os.environ["KUZU_DATABASE_PATH"] = kuzu_path
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["TESTING"] = "1"
    
    # --- CRITICAL: Reset Kuzu Singleton to ensure it picks up new Env Vars ---
    import adapters.persistence.kuzu.adapter
    adapters.persistence.kuzu.adapter._kuzu_instance = None
    
    yield {"db": db_path, "kuzu": kuzu_path}
    
    # Cleanup
    shutil.rmtree(temp_dir)

@pytest_asyncio.fixture
async def real_db_session(real_env):
    """Creates a real SQLite session for testing."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{real_env['db']}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_real_ai_quest_flow(real_db_session):
    """
    E2E Test: User Input -> AI Analysis -> DB Update.
    Requires OPENAI_API_KEY / OPENROUTER_API_KEY.
    """
    user_id = "test_user_real"
    
    # 1. User says something triggering Analysis
    user_input = "I did a 5km run this morning."
    
    # Call process_game_logic with INJECTED session
    result = await process_game_logic(user_id, user_input, session=real_db_session)
    
    # 2. Verify AI recognized intent
    assert result.intent in ["ai_response", "action", "chat"]
    print(f"AI Response: {result.text}")
    
    # 3. Verify DB Update
    from app.models.user import User
    user = await real_db_session.get(User, user_id)
    assert user is not None
    assert user.name is not None
    
    # 4. Verify Kuzu Graph Update
    from adapters.persistence.kuzu.adapter import get_kuzu_adapter
    adapter = get_kuzu_adapter() # Now uses test_kuzu
    
    events = adapter.query_recent_context(user_id, 1) # Correct Method Name
    assert len(events) > 0 or result.intent == "ai_response"
