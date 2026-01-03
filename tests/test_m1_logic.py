import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.user import User
from app.services.user_service import user_service
from app.services.accountant import accountant

# Setup In-Memory DB for Logic Verification
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_accountant_logic():
    # Test XP Math
    xp = accountant.calculate_xp("STR", "E") # Easy
    assert xp > 0
    
    user = User(id="test", str_xp=0, str=1)
    accountant.apply_xp(user, "STR", 150)
    # 150 XP -> Level 2 (1 + floor(1.5))?
    assert user.str_xp == 150
    assert user.str == 2

@pytest.mark.asyncio
async def test_user_service_flow(db_session):
    # Test "End-to-End" Logic with DB
    line_id = "user_123"
    
    # 1. Create User implicitly
    msg = await user_service.process_action(db_session, line_id, "Gym 1 hour")
    
    # 2. Verify DB state
    user = await user_service.get_or_create_user(db_session, line_id)
    assert user.id == line_id
    assert user.str > 1 # Should have gained STR from "Gym"
    assert "Logged: STR" in msg.text
