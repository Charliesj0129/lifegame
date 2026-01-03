from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# For local dev without Docker, allow overriding via env or fallback? 
# Settings has SQLALCHEMY_DATABASE_URI.
# If connection fails, we might crash, but that's expected.

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI, 
    echo=False,
    pool_size=3,              # Low memory profile for Free Tier
    max_overflow=2,
    pool_recycle=300,         # Recycle every 5m to prevent Azure timeout
    pool_pre_ping=True        # Verify connection before usage
)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
