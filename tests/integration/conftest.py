import pytest
import pytest_asyncio
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from app.models.base import Base

# We define this as a separate plugin or just import it in integration tests
# To avoid spinning up containers for unit tests, we put this in tests/integration/conftest.py if possible,
# or we use a marker.

@pytest.fixture(scope="session")
def postgres_container():
    """
    Spins up a Postgres container for the duration of the test session.
    """
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres

@pytest_asyncio.fixture(scope="session")
async def integration_db_engine(postgres_container):
    """
    Creates an async engine connected to the test container.
    """
    # testcontainers provides synch driver url usually (psycopg2)
    # We need to convert it to async (postgresql+asyncpg)
    db_url = postgres_container.get_connection_url()
    # Replace driver
    async_db_url = db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    # Or just "postgresql://" if using older testcontainers, but usually it specifies driver.
    if "asyncpg" not in async_db_url:
         async_db_url = async_db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(async_db_url, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    
    await engine.dispose()

@pytest_asyncio.fixture
async def integration_session(integration_db_engine):
    """
    Provides a clean session for each test.
    Transactions are rolled back after each test to ensure isolation.
    """
    connection = await integration_db_engine.connect()
    transaction = await connection.begin()
    
    async_session = sessionmaker(
        integration_db_engine, 
        class_=AsyncSession, 
        expire_on_commit=False,
        bind=connection
    )
    
    async with async_session() as session:
        yield session
        
    await transaction.rollback()
    await connection.close()
