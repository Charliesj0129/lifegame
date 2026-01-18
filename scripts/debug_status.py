import asyncio
import logging
import sys
from app.core.database import AsyncSessionLocal
from app.main import handle_status
from app.models.user import User

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_status():
    logger.info("--- Starting Debug Status ---")
    async with AsyncSessionLocal() as session:
        # ensuring user exists
        user_id = "debug_user_001"
        user = await session.get(User, user_id)
        if not user:
            user = User(id=user_id, name="Debug Hero", gold=100, xp=50)
            session.add(user)
            await session.commit()
            logger.info(f"Created debug user: {user_id}")

        try:
            logger.info(f"Invoking handle_status for {user_id}...")
            result = await handle_status(session, user_id, "狀態")
            logger.info(f"Result: {result.text}")
            if result.intent == "status_critical_error" or result.intent == "status_render_error":
                logger.error("!!! STATUS FAILED !!!")
                sys.exit(1)
            else:
                logger.info(">>> STATUS SUCCESS <<<")
        except Exception:
            logger.exception("CRITICAL UNHANDLED EXCEPTION")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_status())
