import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import get_db
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.base import Base

# Setup Test DB Override
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
AsyncTestSession = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncTestSession() as session:
        yield session

@pytest.mark.asyncio
async def test_health_endpoint():
    """
    Verifies that the /health endpoint returns 200 and DB status.
    """
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
        
    app.dependency_overrides.clear()
        
    assert response.status_code == 200, f"Health check failed: {response.text}"
    data = response.json()
    expected_keys = {"status", "db", "version"}
    assert expected_keys.issubset(data.keys())
    assert data["db"] == "connected"
