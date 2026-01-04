import asyncio
import logging
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.daily_briefing_service import daily_briefing
from app.core.database import AsyncSessionLocal
from sqlalchemy.future import select
import json

logging.basicConfig(level=logging.INFO)

async def test_briefing():
    print("\n--- Testing Daily Briefing ---")
    user_id = "U_TEST_VIPER"
    
    # Ensure User Exists
    async with AsyncSessionLocal() as session:
        from app.models.user import User
        res = await session.execute(select(User).where(User.id == user_id))
        if not res.scalars().first():
            session.add(User(id=user_id, name="Viper Test Subject", level=5, xp=1200))
            await session.commit()
            print("✅ Created Test User.")
    
    # Mocking get_messaging_api return value
    # We use AsyncMock for the api client methods
    mock_api = MagicMock()
    # push_message is async, so return an awaitable
    mock_api.push_message = AsyncMock()

    with patch("app.services.daily_briefing_service.get_messaging_api", return_value=mock_api):
        # Run Service
        await daily_briefing.process_daily_briefing(user_id)
        
        # Verification
        if mock_api.push_message.called:
            print("✅ Push Message Triggered.")
            args, _ = mock_api.push_message.call_args
            req = args[0] # PushMessageRequest
            print(f"To User: {req.to}")
            print("Flex Contents:")
            
            # Message object in req.messages list
            msg = req.messages[0]
            # msg is a FlexSendMessage object. We need to serialize it or check .contents
            # If linebot sdk v3, it has .to_dict() or we access .contents
            if hasattr(msg, "contents"):
                 # FlexContainer object, just print string rep
                 print(msg.contents)
            else:
                 print(msg) 
            
            # Verify Viper Logic from DB
            async with AsyncSessionLocal() as session:
                from app.models.quest import Rival
                # select is already imported globally
                res = await session.execute(select(Rival).where(Rival.user_id == user_id))
                viper = res.scalars().first()
                if viper:
                    print(f"\n🐍 Viper Status: Lv.{viper.level} (XP: {viper.xp})")
                else:
                    print("❌ Viper not found.")
        else:
            print("❌ Push Message NOT Triggered.")

if __name__ == "__main__":
    asyncio.run(test_briefing())
