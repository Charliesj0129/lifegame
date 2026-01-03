import asyncio
from app.core.database import engine
from app.models.base import Base
# Import models to ensure they are registered in Base.metadata
from app.models.user import User
from app.models.action_log import ActionLog
from app.models.gamification import Item, UserItem

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database Initialized.")

if __name__ == "__main__":
    asyncio.run(init_models())
