import asyncio
import logging
from app.core.database import engine as default_engine
from app.models.base import Base
# Import ALL models to ensure they are in metadata
from app.models.user import User
from app.models.action_log import ActionLog
from app.models.quest import Quest, Goal, Rival

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration_m7")

async def migrate(engine_override=None):
    target_engine = engine_override or default_engine
    logger.info("Starting M7 Table Creation...")
    
    try:
        async with target_engine.begin() as conn:
            # check_first=True is inherent in create_all for many dialects, 
            # but explicit error handling is better for some Drivers.
            await conn.run_sync(Base.metadata.create_all)
        logger.info("M7 Tables Created (Idempotent).")
    except Exception as e:
        # Log critical error but maybe don't crash if it's just "already exists" deep error
        # However, create_all usually handles "IF NOT EXISTS" well.
        # This catch is for Connection Refused or other critical infras issues.
        logger.error(f"Migration Failed: {e}")
        # We re-raise because if DB is truly down, app shouldn't start?
        # OR we swallow to allow 'partial' start if that was the goal.
        # Plan says: "log warnings but doesn't crash... if it's just Table exists"
        # Since create_all IS safe for "Table exists", this catch is mostly for
        # unexpected errors. We'll log and re-raise to be safe, 
        # but the standard create_all shouldn't crash on existing tables.
        raise e

if __name__ == "__main__":
    try:
        asyncio.run(migrate())
    except Exception as e:
        logger.critical(f"Fatal Migration Error: {e}")
        exit(1)
