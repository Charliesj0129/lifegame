import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from application.services.context_service import ContextService
from legacy.models.action_log import ActionLog
from app.models.user import User
from app.models.base import Base

# Use in-memory DB for test
@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Create ActionLog table manually if not in Base? 
        # ActionLog might use a different Base/metadata in legacy?
        # Let's check imports. ActionLog imports Base from app.models.base usually.
        # But if it uses legacy base... 
        # Assuming ActionLog uses the same Base.
        
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_context_aggregation(db_session):
    svc = ContextService()
    
    # Setup Data
    user = User(id="test_u1", name="Tester", level=5, hp=100)
    db_session.add(user)
    
    log = ActionLog(
        user_id="test_u1", 
        action_text="Did pushups", 
        timestamp=datetime.now(),
        attribute_tag="STR",
        difficulty_tier="E"
    )
    db_session.add(log)
    await db_session.commit()
    
    # Execute
    context = await svc.get_working_memory(db_session, "test_u1")
    
    # Verify
    assert "Did pushups" in context["short_term_history"]
    assert context["user_state"]["level"] == 5
    # Long term might be empty from Kuzu unless we seed it, but the key should exist
    assert "long_term_context" in context
