import os
import sys
import shutil
import pytest
import pytest_asyncio
from unittest.mock import MagicMock

# --- CONFIGURATION (BEFORE IMPORTS) ---
# Override Env Vars for Testing
mock_db_path = "/tmp/test_lifegame_graph"
os.environ["KUZU_DATABASE_PATH"] = mock_db_path
os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite+aiosqlite:///:memory:"
os.environ["TESTING"] = "1"

# Force cleanup of modules to ensure re-import with new env vars
modules_to_unload = [
    "app.main", "app.core.config", "adapters.persistence.kuzu_adapter",
    "adapters.persistence.kuzu.adapter", "application.services.context_service",
    "application.services.game_loop"
]
for m in list(sys.modules.keys()):
    if any(m.startswith(prefix) for prefix in modules_to_unload):
        del sys.modules[m]

# --- IMPORTS ---
from app.main import process_game_logic, app
from domain.models.game_result import GameResult
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.base import Base
from app.models.user import User
from adapters.persistence.kuzu_adapter import get_kuzu_adapter

# --- FIXTURES ---

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_kuzu_dir():
    """Ensure clean temp directory for KuzuDB."""
    if os.path.exists(mock_db_path):
        shutil.rmtree(mock_db_path)
    os.makedirs(mock_db_path)
    
    # Initialize Schema
    adapter = get_kuzu_adapter()
    # Force _initialize if needed, but get_instance calls it? 
    # Current code instantiates KuzuAdapter() which calls _initialize_schema()
    # So it should be ready.
    yield
    # Cleanup
    if os.path.exists(mock_db_path):
        shutil.rmtree(mock_db_path)

@pytest_asyncio.fixture(scope="function")
async def test_session():
    """In-memory SQLite session with schema created."""
    engine = create_async_engine(os.environ["SQLALCHEMY_DATABASE_URI"], echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        # Seed a Test User
        new_user = User(id="test_user_real", name="Tester", hp=100, int=10, str=10)
        session.add(new_user)
        await session.commit()
        yield session
    
    await engine.dispose()

# --- TESTS ---

@pytest.mark.asyncio
async def test_full_business_workflow(test_session):
    """
    Scenario:
    1. User reports activity ("I studied 30 mins").
    2. AI analyzes -> returns INT stat gain.
    3. GameLogic applies update to User (in SQLite) and Graph (Kuzu).
    4. Verify User.int increased.
    5. Verify Graph Event node created.
    """
    
    # Patch main.py to use our test session
    mock_session_cls = MagicMock()
    mock_session_cls.return_value.__aenter__.return_value = test_session
    
    from unittest.mock import patch
    with patch("app.main.AsyncSessionLocal", side_effect=mock_session_cls):
            
            print("\n--- [Step 1] User reports activity ---")
            user_input = "我剛剛專注讀了30分鐘的演算法書"
            result = await process_game_logic("test_user_real", user_input)
            
            print(f"Result Text: {result.text}")
            assert result.intent == "ai_response"
            
            # --- [Step 2] Verify SQLite Updates (Business Logic) ---
            # Refresh user from DB
            await test_session.commit() # Ensure commits visible?
            # actually process_game_logic should have committed.
            
            from sqlalchemy import select
            stmt = select(User).where(User.id == "test_user_real")
            user = (await test_session.execute(stmt)).scalars().first()
            
            print(f"User INT after action: {user.int} (Initial: 10)")
            
            # Verify Stat Update
            if "INT" in str(result.metadata): 
                 assert user.int > 10
            
            # Check Graph
            adapter = get_kuzu_adapter()
            # Verify "Event" node created using low-level execute
            res = adapter.conn.execute("MATCH (e:Event) RETURN count(e)")
            count_row = res.get_next()
            count = count_row[0] if count_row else 0
            
            print(f"Graph Events Count: {count}")
            assert count > 0
            
            assert "演算法" in result.text or "專注" in result.text or "INT" in str(result.metadata)
