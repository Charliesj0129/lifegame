import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.gamification import Item, UserItem
from application.services.inventory_service import inventory_service


# Setup in-memory DB for test
@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session


@pytest.mark.asyncio
async def test_inventory_flow(db_session):
    user_id = "test_user_inv"

    # 1. Seed
    await inventory_service.seed_default_items_if_needed(db_session)

    # Verify Items exist
    from sqlalchemy import select

    items = (await db_session.execute(select(Item))).scalars().all()
    assert len(items) >= 4
    potion = next(i for i in items if "藥水" in i.name)

    # 2. Add Item
    await inventory_service.add_item(db_session, user_id, potion.id, 5)

    # 3. Get Inventory (Returns list of tuples (Item, Qty))
    inv = await inventory_service.get_inventory(db_session, user_id)
    assert len(inv) == 1
    assert inv[0][0].id == potion.id
    assert inv[0][1] == 5

    # 4. Remove Item (partial)
    success = await inventory_service.remove_item(db_session, user_id, potion.id, 2)
    assert success is True
    inv = await inventory_service.get_inventory(db_session, user_id)
    assert inv[0][1] == 3

    # 5. Remove Item (full)
    success = await inventory_service.remove_item(db_session, user_id, potion.id, 3)
    assert success is True
    inv = await inventory_service.get_inventory(db_session, user_id)
    assert len(inv) == 0
