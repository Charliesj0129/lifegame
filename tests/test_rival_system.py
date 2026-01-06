import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.user import User
from app.models.quest import Rival
from app.services.rival_service import rival_service
from app.services.ai_engine import ai_engine
import datetime

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with TestSession() as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_rival_creation(db_session):
    user_id = "U_RIVAL_TEST"
    rival = await rival_service.get_or_create_rival(db_session, user_id)
    assert rival.user_id == user_id
    assert rival.name == "Viper"
    assert rival.level >= 1

@pytest.mark.asyncio
async def test_get_taunt_ai_integration(db_session):
    # Setup
    user = User(id="u_taunt", name="Hero", level=5)
    rival = Rival(user_id="u_taunt", name="Viper", level=10) # Rival Stronger
    
    # Mock AI
    with patch("app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = {"taunt": "你太弱了。"}
        
        taunt = await rival_service.get_taunt(db_session, user, rival)
        
        # Verify
        assert "你太弱" in taunt
        assert taunt.startswith("Viper：「")
        
        # Check Prompt Context
        args, _ = mock_ai.call_args
        assert "Rival is stronger" in args[1] # User prompt
        assert "Viper Lv.10 vs User Lv.5" in args[1]

@pytest.mark.asyncio
async def test_inactivity_penalty(db_session):
    # Setup User inactive for 3 days
    past = datetime.datetime.now() - datetime.timedelta(days=4) # > 3 days diff
    user = User(id="u_lazy", name="Lazy", level=5, xp=1000, gold=1000, last_active_date=past)
    db_session.add(user)
    await db_session.commit()
    
    # Run Encounter
    # We need to mock get_or_create_rival to return a rival that levels up
    # actually process_encounter calls get_or_create.
    
    narrative = await rival_service.process_encounter(db_session, user)
    
    # Check Logic
    # 4 days gap roughly = 3 missed days?
    # Logic: delta.days - 1. 4 days ago -> delta=4. missed=3.
    # Theft: 5% * 3 = 15%. 150 XP/Gold.
    
    await db_session.refresh(user)
    assert user.xp < 1000
    assert user.gold < 1000
    assert "入侵警報" in narrative

    # Check Rival leveled up (3 missed days * 100 XP = 300 XP. Lv 1 + 0 = 1. No level up unless initial XP was high?
    # Logic: new_level = 1 + (xp // 1000). 300 XP is still Lv 1.
    # So no level up message unless we boost initial XP.
