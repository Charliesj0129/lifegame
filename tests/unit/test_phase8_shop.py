import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.base import Base
from app.models.user import User
from legacy.models.gamification import Item, UserItem, ItemRarity, ItemType
from legacy.services.shop_service import shop_service
from legacy.services.inventory_service import inventory_service
import uuid


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
async def test_shop_buy_flow(db_session):
    user_id = "test_user_shop"

    # 0. Setup User with Gold
    user = User(id=user_id, name="Shopper", gold=1000)
    db_session.add(user)

    # 1. Seed Items
    await inventory_service.seed_default_items_if_needed(db_session)
    items = (await db_session.execute(select(Item))).scalars().all()
    potion = next(i for i in items if "藥水" in i.name)  # Price 50
    coin = next(i for i in items if "硬幣" in i.name)  # Price 500

    # 2. Buy Item (Success)
    # Ensure item is purchasable
    potion.is_purchasable = True
    db_session.add(potion)
    await db_session.commit()

    res = await shop_service.buy_item(db_session, user_id, potion.id)
    assert res["success"] is True
    assert "已購買" in res["message"]

    # Verify State
    await db_session.refresh(user)
    assert user.gold == 1000 - 50

    inv = await inventory_service.get_inventory(db_session, user_id)
    assert len(inv) == 1
    assert inv[0][0].id == potion.id

    # 3. Buy Item (Fail - Not Purchasable)
    # Coin is not set to purchasable by default seed logic (usually)
    # Check seed logic: wait, seed logic doesn't set is_purchasable=True explicitly?
    # Let's force verify coin status
    coin.is_purchasable = False
    db_session.add(coin)
    await db_session.commit()

    res = await shop_service.buy_item(db_session, user_id, coin.id)
    assert res["success"] is False
    assert "不可購買" in res["message"]

    # 4. Buy Item (Fail - Poor)
    user.gold = 0
    db_session.add(user)
    await db_session.commit()

    res = await shop_service.buy_item(db_session, user_id, potion.id)
    assert res["success"] is False
    assert "金幣不足" in res["message"]
