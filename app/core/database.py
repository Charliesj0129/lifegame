from sqlalchemy import text  # Import text for PRAGMA
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Database Engine Configuration
engine_args = {"echo": False, "pool_pre_ping": True}

# Optimization for Postgres Pool
if "sqlite" not in settings.DATABASE_URL:
    engine_args.update({"pool_size": 3, "max_overflow": 2, "pool_recycle": 300})

engine = create_async_engine(settings.DATABASE_URL, **engine_args)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """Dependency Injection provider for FastAPI"""
    async with AsyncSessionLocal() as session:
        # Enable WAL mode for SQLite to reduce locking
        if "sqlite" in settings.DATABASE_URL:
            await session.execute(text("PRAGMA journal_mode=WAL;"))
            await session.execute(text("PRAGMA synchronous=NORMAL;"))  # Optional but faster

        yield session
