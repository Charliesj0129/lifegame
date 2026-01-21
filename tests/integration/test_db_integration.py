import pytest
from sqlalchemy import select, text

from app.models.user import User


@pytest.mark.asyncio
async def test_postgres_connection(integration_session):
    """
    Verifies that we can connect to the real Postgres container and execute a query.
    """
    result = await integration_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_user_persistence_real_db(integration_session):
    """
    Verifies full round-trip persistence of a User entity in a real Postgres DB.
    """
    user = User(id="real_user_1", name="Integration Hero", gold=500)
    integration_session.add(user)
    await integration_session.flush()  # Flush to DB (transaction still open)

    # Verify retrieval
    stmt = select(User).where(User.id == "real_user_1")
    result = await integration_session.execute(stmt)
    fetched = result.scalars().first()

    assert fetched is not None
    assert fetched.name == "Integration Hero"
    assert fetched.gold == 500
