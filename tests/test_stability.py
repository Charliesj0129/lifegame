import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from scripts.migrate_m7 import migrate
from app.models.base import Base

@pytest.mark.asyncio
async def test_migration_idempotency():
    """
    Verifies that the migration script can be run multiple times 
    without crashing (Idempotency).
    """
    # 1. Setup specific test DB (file-based to verify across connections)
    import os
    db_file = "./test_stability.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        
    db_url = f"sqlite+aiosqlite:///{db_file}"
    test_engine = create_async_engine(db_url)
    
    # 2. Run Migration First Time
    try:
        await migrate(engine_override=test_engine)
    except Exception as e:
        pytest.fail(f"First migration failed: {e}")
        
    # Check tables exist
    async with test_engine.connect() as conn:
        # SQLite specific check
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
        assert result.scalar() == 'users'

    # 3. Run Migration Second Time (Should not fail)
    try:
        await migrate(engine_override=test_engine)
    except Exception as e:
        pytest.fail(f"Second migration (idempotency check) failed: {e}")
        
    await test_engine.dispose()
