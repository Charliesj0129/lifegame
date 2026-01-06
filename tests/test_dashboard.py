from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.models.user import User
from app.models.quest import Rival, Quest

client = TestClient(app)

from app.core.database import get_db
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Removed test_dashboard_endpoint stub


# Let's try a simpler integration test style using the InMemory DB fixture we used elsewhere
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.base import Base

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def override_get_db():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with TestSession() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_dashboard_full_stack(override_get_db):
    # Setup Data in DB
    session = override_get_db
    user = User(id="u_dash", name="Visual", level=10, xp=1000)
    session.add(user)

    rival = Rival(user_id="u_dash", name="Viper", level=12)
    session.add(rival)

    q1 = Quest(
        user_id="u_dash",
        title="Visual Quest",
        difficulty_tier="C",
        xp_reward=50,
        status="ACTIVE",
    )
    session.add(q1)

    await session.commit()

    # Override App Dependency
    app.dependency_overrides[get_db] = lambda: session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/dashboard/u_dash")

    assert response.status_code == 200
    assert "Visual (Lv.10)" in response.text
    assert "Viper" in response.text
    assert "Visual Quest" in response.text
    assert "系統狀態" in response.text  # Chart Title
