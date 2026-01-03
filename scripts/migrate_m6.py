import asyncio
from sqlalchemy import text
from app.core.database import engine

async def migrate():
    print("Starting M6 Migration...")
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN streak_count INTEGER DEFAULT 0"))
            print("Added streak_count column.")
        except Exception as e:
            print(f"Skipping streak_count (probably exists): {e}")

        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN last_active_date TIMESTAMP WITH TIME ZONE"))
            print("Added last_active_date column.")
        except Exception as e:
            print(f"Skipping last_active_date (probably exists): {e}")

    print("Migration Complete.")

if __name__ == "__main__":
    asyncio.run(migrate())
