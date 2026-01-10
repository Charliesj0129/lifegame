from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text # Import text for PRAGMA
from app.core.config import settings

# For local dev without Docker, allow overriding via env or fallback?
# Settings has SQLALCHEMY_DATABASE_URI.
# If connection fails, we might crash, but that's expected.

engine_args = {"echo": False, "pool_pre_ping": True}

if "sqlite" not in settings.SQLALCHEMY_DATABASE_URI:
    engine_args.update({"pool_size": 3, "max_overflow": 2, "pool_recycle": 300})

engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, **engine_args)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        # Enable WAL mode for SQLite to reduce locking
        if "sqlite" in settings.SQLALCHEMY_DATABASE_URI:
            await session.execute(text("PRAGMA journal_mode=WAL;"))
            await session.execute(text("PRAGMA synchronous=NORMAL;")) # Optional but faster
            
        yield session
