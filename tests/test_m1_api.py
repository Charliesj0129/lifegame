import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.database import get_db
from app.models.base import Base
from app.models.base import Base
from app.models.user import User
from app.models.gamification import Item # Force registration

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def override_get_db():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_get_user_status_404():
    # Setup DB override
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async def _get_test_db():
        async with TestSession() as session:
             yield session

    app.dependency_overrides[get_db] = _get_test_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/users/unknown_user/status")
        # Should be 404
        assert response.status_code == 404
    
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_webhook_creates_user():
    # Mock Line & DB
    # We need to patch 'AsyncSessionLocal' in webhook.py or use dependency injection if refactored.
    # Current webhook.py imports 'AsyncSessionLocal' directly. This is hard to test with override.
    # We should have used `Depeneds(get_db)` in webhook handler, but LineBot middleware makes it tricky.
    # So we patch `app.api.webhook.AsyncSessionLocal`.
    
    # Create valid DB engine for patch
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Mock the MessagingApi to avoid error
    with patch("app.api.webhook.get_messaging_api") as mock_get_api, \
         patch("app.core.database.AsyncSessionLocal", TestSession), \
         patch("app.core.config.settings.LINE_CHANNEL_SECRET", "secret"), \
         patch("app.core.config.settings.LINE_CHANNEL_ACCESS_TOKEN", "token"):
        
        mock_api_instance = AsyncMock()
        mock_get_api.return_value = mock_api_instance
        
        # Mock Handler Signature validation
        with patch("app.services.line_bot.AsyncWebhookHandler.handle", new_callable=AsyncMock) as mock_handle:      
             # Wait. If we mock `handler.handle`, we skip the logic inside `handle_message`.
             # We want to run `handle_message` logic.
             # So we should NOT mock `handle`, but rely on the real handler dispatching to `handle_message`.
             # We just need to mock signature validation or manually invoke logic?
             # Let's try sending a request.
             pass

    # Actually, testing `handle_message` directly is easier than full webhook flow sometimes, 
    # but full flow ensures router works.
    # Issue: `AsyncWebhookHandler` validates signature.
    # Let's mock `parser.signature_validator.validate_signature`.
        # Issue: Handler is singleton instantiated at import time. Patching Class doesn't affect instance.
        # We must patch the instance.
        from app.api.webhook import webhook_handler
        
        # Patch validator on the existing parser instance
        with patch.object(webhook_handler.parser.signature_validator, "validate", return_value=True):
             
             # We also need to mock parser.parse on the instance
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
             
             # Parser.parse is called. We need to patch webhook_handler.parser.parse
             with patch.object(webhook_handler.parser, "parse", return_value=[mock_event]):

                     async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                        response = await ac.post(
                            "/callback", 
                            content="dummy", 
                            headers={"X-Line-Signature": "sig"}
                        )
                        assert response.status_code == 200
                        assert response.json() == "OK"
                        
                        # Debug: Check what the bot replied
                        args, kwargs = mock_api_instance.reply_message.call_args
                        reply_req = args[0]
                        msg_obj = reply_req.messages[0]
                        if hasattr(msg_obj, 'text') and msg_obj.type == 'text':
                            reply_text = msg_obj.text
                        else:
                            reply_text = getattr(msg_obj, 'alt_text', str(msg_obj))
                            
                        print(f"\n[DEBUG] Reply Text: {reply_text}")
                        assert "System Glitch" not in reply_text, f"Webhook Failed: {reply_text}"
                        
                        # Verify User Created in DB
                        # We need to verify directly against DB or via status endpoint?
                        # Let's verify via status endpoint since we cover that.
                        user_res = await ac.get("/users/u_test_webhook/status")
                        assert user_res.status_code == 200
                        assert user_res.json()["attributes"]["STR"] > 1

@pytest.mark.asyncio
async def test_end_to_end_logic_via_api():
    # Since Webhook is hard to test e2e without complex mocking, 
    # Let's verify via the User Service directly vs the DB, which we did in `test_m1_logic.py`.
    # AND verify the `users` endpoint works with data.
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Seed Data
    async with TestSession() as session:
        user = User(id="u1", name="Charlie", str=5, int=0, vit=0, wis=0, cha=0)
        session.add(user)
        await session.commit()
    
    async def _get_test_db():
        async with TestSession() as session:
             yield session

    app.dependency_overrides[get_db] = _get_test_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/users/u1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "u1"
        assert data["attributes"]["STR"] == 5
