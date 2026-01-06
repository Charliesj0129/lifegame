import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, AsyncMock
from app.main import app
from app.core.database import get_db
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
    
    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with TestSession() as session:
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
    assert "⚡" in msg.text

@pytest.mark.asyncio
async def test_get_user_status_404(db_session):
    # Use dependency injection override with the shared db_session
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/users/unknown_user/status")
        # Should be 404
        assert response.status_code == 404
    
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_webhook_creates_user(db_session):
    # Mock Line & DB
    # We need to patch 'AsyncSessionLocal' in webhook.py or use dependency injection if refactored.
    # Current webhook.py imports 'AsyncSessionLocal' directly. This is hard to test with override.
    # We should have used `Depeneds(get_db)` in webhook handler, but LineBot middleware makes it tricky.
    # So we patch `app.api.webhook.AsyncSessionLocal`.
    
    # Create session factory mock
    TestSession = lambda: db_session # This isn't quite right for context manager mock
    
    # Properly mock AsyncSessionLocal to return an async context manager that yields our db_session
    class MockSessionContext:
        def __init__(self):
            pass
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # Mock the MessagingApi to avoid error
    with patch("app.api.webhook.get_messaging_api") as mock_get_api, \
         patch("app.core.database.AsyncSessionLocal", side_effect=MockSessionContext), \
         patch("app.core.config.settings.LINE_CHANNEL_SECRET", "secret"), \
         patch("app.core.config.settings.LINE_CHANNEL_ACCESS_TOKEN", "token"):
        
        mock_api_instance = AsyncMock()
        mock_get_api.return_value = mock_api_instance
        
        # Patch signature validator
        from app.api.webhook import webhook_handler
        with patch.object(webhook_handler.parser.signature_validator, "validate", return_value=True):
             
             # Mock parser.parse to return a fake event
             from linebot.v3.webhooks import MessageEvent, TextMessageContent, DeliveryContext, UserSource
             mock_event = MessageEvent(
                 type="message",
                 mode="active",
                 timestamp=1234567890,
                 source=UserSource(type="user", userId="u_test_webhook"),
                 webhookEventId="wid",
                 deliveryContext=DeliveryContext(isRedelivery=False),
                 replyToken="r_token",
                 message=TextMessageContent(id="mid", type="text", text="Gym 1 hour", quoteToken="q_token")
             )
             
             with patch.object(webhook_handler.parser, "parse", return_value=[mock_event]):

                     async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                        response = await ac.post(
                            "/callback", 
                            content="dummy", 
                            headers={"X-Line-Signature": "sig"}
                        )
                        assert response.status_code == 200
                        assert response.json() == "OK"
                        
                        # Verify User Created in DB via status endpoint
                        # We need to override get_db for the *get* request which uses Depends(get_db)
                        app.dependency_overrides[get_db] = lambda: db_session
                        
                        user_res = await ac.get("/users/u_test_webhook/status")
                        app.dependency_overrides.clear()
                        
                        assert user_res.status_code == 200
                        assert user_res.json()["attributes"]["力量"] > 1

@pytest.mark.asyncio
async def test_end_to_end_logic_via_api(db_session):
    # Seed Data
    user = User(id="u1", name="Charlie", str=5, int=0, vit=0, wis=0, cha=0)
    db_session.add(user)
    await db_session.commit()
    
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/users/u1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "u1"
        assert data["attributes"]["力量"] == 5
    
    app.dependency_overrides.clear()
