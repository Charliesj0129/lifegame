import pytest
import pytest_asyncio
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from adapters.persistence.sqlite.base_repository import SqlAlchemyRepository

Base = declarative_base()


class DummyEntity(Base):
    __tablename__ = "dummy"
    id = Column(Integer, primary_key=True)
    name = Column(String)


@pytest_asyncio.fixture
async def db_session():
    # Use in-memory SQLite for speed
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_repository_crud(db_session):
    repo = SqlAlchemyRepository(db_session, DummyEntity)

    # ADD
    new_entity = DummyEntity(id=1, name="Test Item")
    await repo.add(new_entity)
    await db_session.commit()  # UnitOfWork role

    # GET
    item = await repo.get(1)
    assert item is not None
    assert item.name == "Test Item"

    # LIST
    items = await repo.list()
    assert len(items) == 1

    # SAVE/UPDATE
    item.name = "Updated Item"
    await repo.save(item)
    await db_session.commit()

    updated = await repo.get(1)
    assert updated.name == "Updated Item"

    # DELETE
    success = await repo.delete(1)
    assert success is True
    await db_session.commit()

    missing = await repo.get(1)
    assert missing is None
