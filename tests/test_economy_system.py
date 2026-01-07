import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.base import Base
from app.models.user import User
from legacy.models.gamification import Item, UserItem
from legacy.services.shop_service import shop_service

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with TestSession() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_shop_listing(db_session):
    # Setup Items
    i1 = Item(id="POTION", name="Potion", price=50, is_purchasable=True)
    i2 = Item(id="KEY", name="Key", price=999, is_purchasable=False)
    db_session.add_all([i1, i2])
    await db_session.commit()

    items = await shop_service.list_shop_items(db_session)
    assert len(items) == 1
    assert items[0].id == "POTION"


@pytest.mark.asyncio
async def test_buy_item_success(db_session):
    # Setup
    u = User(id="u1", name="Buyer", gold=100)
    i = Item(id="POTION", name="Potion", price=50, is_purchasable=True)
    db_session.add_all([u, i])
    await db_session.commit()

    # Buy
    res = await shop_service.buy_item(db_session, "u1", "POTION")
    assert res["success"] is True

    # Check Gold
    await db_session.refresh(u)
    assert u.gold == 50

    # Check Inventory
    stmt = select(UserItem).where(
        UserItem.user_id == "u1", UserItem.item_id == "POTION"
    )
    result = await db_session.execute(stmt)
    inv = result.scalars().first()
    assert inv is not None
    assert inv.quantity == 1


@pytest.mark.asyncio
async def test_buy_item_insufficient_funds(db_session):
    # Setup
    u = User(id="u2", name="Broke", gold=10)
    i = Item(id="SWORD", name="Sword", price=100, is_purchasable=True)
    db_session.add_all([u, i])
    await db_session.commit()

    # Buy
    res = await shop_service.buy_item(db_session, "u2", "SWORD")
    assert res["success"] is False
    assert "金幣不足" in res["message"]

    # Check Gold Unchanged
    await db_session.refresh(u)
    assert u.gold == 10

    # Check Inventory Empty
    stmt = select(UserItem).where(UserItem.user_id == "u2")
    result = await db_session.execute(stmt)
    inv = result.scalars().first()
    assert inv is None
