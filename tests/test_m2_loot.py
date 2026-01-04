import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from unittest.mock import patch, AsyncMock
from app.main import app
from app.core.database import get_db
from app.models.base import Base
from app.models.gamification import Item, ItemRarity, ItemType, UserItem
from app.models.user import User
from app.services.loot_service import loot_service

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with TestSession() as session:
        yield session
    
    await engine.dispose()

@pytest_asyncio.fixture
async def client(test_db):
    async def _get_test_db():
        yield test_db

    app.dependency_overrides[get_db] = _get_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_loot_drop_end_to_end(test_db):
    # 1. Seed Item
    item = Item(id="POTION_TEST", name="Test Potion", rarity=ItemRarity.COMMON)
    test_db.add(item)
    await test_db.commit()
    
    # 2. Patch LootService to guarantee drop
    with patch.object(loot_service, "_roll_for_drop", return_value=True), \
         patch.object(loot_service, "_select_rarity", return_value=ItemRarity.COMMON):
        
        # 3. Process Action via Service directly
        from app.services.user_service import user_service
        msg = await user_service.process_action(test_db, "u_loot_test", "Gym 1 hour")
        
        # 4. Verify Message (Result Object)
        assert msg.loot_name == "Test Potion"
        # msg.text does not contain loot info anymore
        assert "🎁 LOOT" in msg.to_text_message()
        
        # 5. Verify Database Persistence
        res = await test_db.execute(select(UserItem).where(UserItem.user_id == "u_loot_test"))
        user_items = res.scalars().all()
        assert len(user_items) == 1
        assert user_items[0].item_id == "POTION_TEST"
        assert user_items[0].quantity == 1

@pytest.mark.asyncio
async def test_inventory_api(test_db, client):
    # 1. Seed Data
    user = User(id="u_inv", name="Inv Tester")
    item = Item(id="POTION_INV", name="Inv Potion", rarity=ItemRarity.EPIC, type=ItemType.CONSUMABLE)
    test_db.add(user)
    test_db.add(item)
    await test_db.commit()
    
    u_item = UserItem(user_id="u_inv", item_id="POTION_INV", quantity=10)
    test_db.add(u_item)
    await test_db.commit()
    
    # 2. Call API
    response = await client.get("/users/u_inv/inventory")
    print(response.json())
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Inv Potion"
    assert data[0]["quantity"] == 10
    assert data[0]["rarity"] == "EPIC"

@pytest.mark.asyncio
async def test_status_card_rendering():
    from app.services.flex_renderer import flex_renderer
    from app.models.user import User
    
    user = User(id="u_stat", name="Hero", level=5, str=10, int=5, vit=5, wis=5, cha=5, gold=100)
    
    msg = flex_renderer.render_status(user)
    assert msg.alt_text.startswith("Tactical OS:")
    # Verify Pydantic serialization works (no validation errors)
    assert msg.contents.to_dict() is not None
