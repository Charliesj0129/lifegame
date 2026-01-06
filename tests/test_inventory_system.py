import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from unittest.mock import patch
from app.main import app
from app.core.database import get_db
from app.models.base import Base
from app.models.user import User
from app.models.gamification import Item, UserItem, ItemType, ItemRarity
from app.services.inventory_service import inventory_service
from app.services.loot_service import loot_service
from app.services.accountant import accountant

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

@pytest_asyncio.fixture
async def client(db_session):
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_use_item_applies_buff(db_session):
    # Setup
    user = User(id="u_inv", name="Tester")
    db_session.add(user)
    
    item = Item(
        id="POT_INT", 
        name="Brain Potion", 
        type=ItemType.CONSUMABLE,
        effect_meta={"buff": "INT", "multiplier": 2.0, "duration_minutes": 30}
    )
    db_session.add(item)
    
    user_item = UserItem(user_id=user.id, item_id=item.id, quantity=2)
    db_session.add(user_item)
    await db_session.commit()

    # Act
    msg = await inventory_service.use_item(db_session, user.id, "Brain")
    
    # Assert
    assert "Applied 2.0x INT Boost" in msg or "Brain Potion" in msg
    
    # Check Buff
    buffs = await inventory_service.get_active_buffs(db_session, user.id)
    assert len(buffs) == 1
    assert buffs[0].target_attribute == "INT"
    assert buffs[0].multiplier == 2.0
    
    # Check Quantity
    await db_session.refresh(user_item)
    assert user_item.quantity == 1

@pytest.mark.asyncio
async def test_use_item_buff_multiplier_schema(db_session):
    user = User(id="u_inv_schema", name="Tester")
    db_session.add(user)
    
    item = Item(
        id="POT_FOCUS",
        name="Focus Potion",
        type=ItemType.CONSUMABLE,
        effect_meta={"effect": "buff_multiplier", "attribute": "INT", "multiplier": 1.5, "duration_minutes": 45}
    )
    db_session.add(item)
    
    user_item = UserItem(user_id=user.id, item_id=item.id, quantity=1)
    db_session.add(user_item)
    await db_session.commit()

    msg = await inventory_service.use_item(db_session, user.id, "Focus")
    assert "Focus Potion" in msg

    buffs = await inventory_service.get_active_buffs(db_session, user.id)
    assert len(buffs) == 1
    assert buffs[0].target_attribute == "INT"
    assert buffs[0].multiplier == 1.5

@pytest.mark.asyncio
async def test_use_item_grants_xp(db_session):
    user = User(id="u_inv_xp", name="Tester")
    db_session.add(user)
    
    item = Item(
        id="POT_XP",
        name="Small XP Potion",
        type=ItemType.CONSUMABLE,
        effect_meta={"effect": "grant_xp", "amount": 50}
    )
    db_session.add(item)
    
    user_item = UserItem(user_id=user.id, item_id=item.id, quantity=1)
    db_session.add(user_item)
    await db_session.commit()
    user_item_id = user_item.id

    msg = await inventory_service.use_item(db_session, user.id, "XP")
    assert "Small XP Potion" in msg

    await db_session.refresh(user)
    assert user.xp == 50

    deleted_item = await db_session.get(UserItem, user_item_id)
    assert deleted_item is None

@pytest.mark.asyncio
async def test_accountant_applies_buff():
    # Mock buff
    class MockBuff:
        target_attribute = "INT"
        multiplier = 2.0
        
    xp = 100
    buffs = [MockBuff()]
    
    # Matching Attribute
    new_xp = accountant.apply_buffs(xp, buffs, "INT")
    assert new_xp == 200
    
    # Non-matching
    new_xp_str = accountant.apply_buffs(xp, buffs, "STR")
    assert new_xp_str == 100

@pytest.mark.asyncio
async def test_loot_drop_end_to_end(db_session):
    # 1. Seed Item
    item = Item(id="POTION_TEST", name="Test Potion", rarity=ItemRarity.COMMON)
    db_session.add(item)
    await db_session.commit()
    
    # 2. Patch LootService to guarantee drop
    with patch.object(loot_service, "_roll_for_drop", return_value=True), \
         patch.object(loot_service, "_select_rarity", return_value=ItemRarity.COMMON):
        
        # 3. Process Action via Service directly
        from app.services.user_service import user_service
        msg = await user_service.process_action(db_session, "u_loot_test", "Gym 1 hour")
        
        # 4. Verify Message (Result Object)
        assert msg.loot_name == "Test Potion"
        # msg.text does not contain loot info anymore
        assert "🎁 掉寶" in msg.to_text_message()
        
        # 5. Verify Database Persistence
        res = await db_session.execute(select(UserItem).where(UserItem.user_id == "u_loot_test"))
        user_items = res.scalars().all()
        assert len(user_items) == 1
        assert user_items[0].item_id == "POTION_TEST"
        assert user_items[0].quantity == 1

@pytest.mark.asyncio
async def test_inventory_api(db_session, client):
    # 1. Seed Data
    user = User(id="u_inv", name="Inv Tester")
    item = Item(id="POTION_INV", name="Inv Potion", rarity=ItemRarity.EPIC, type=ItemType.CONSUMABLE)
    db_session.add(user)
    db_session.add(item)
    await db_session.commit()
    
    u_item = UserItem(user_id="u_inv", item_id="POTION_INV", quantity=10)
    db_session.add(u_item)
    await db_session.commit()
    
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
    assert msg.alt_text.startswith("戰術系統") or msg.alt_text.startswith("Tactical OS")  # Support Chinese
    # Verify Pydantic serialization works (no validation errors)
    assert msg.contents.to_dict() is not None
