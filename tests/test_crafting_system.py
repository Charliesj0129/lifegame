import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.base import Base
from app.models.user import User
from app.models.gamification import Item, UserItem, Recipe, RecipeIngredient
from app.services.crafting_service import crafting_service

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
async def test_get_available_recipes(db_session):
    # Setup Data
    # Items
    herb = Item(id="HERB", name="Herb")
    potion = Item(id="POTION", name="Potion")
    db_session.add_all([herb, potion])
    
    # Recipe: 2 Herbs -> 1 Potion
    recipe = Recipe(id="R_POTION", name="Brew Potion", result_item_id="POTION", result_quantity=1)
    db_session.add(recipe)
    await db_session.commit()
    
    # Ingredients
    ing = RecipeIngredient(recipe_id="R_POTION", item_id="HERB", quantity_required=2)
    db_session.add(ing)
    
    # User with 1 Herb (Not enough)
    user_item = UserItem(user_id="u1", item_id="HERB", quantity=1)
    db_session.add(user_item)
    
    await db_session.commit()
    
    # Action
    recipes = await crafting_service.get_available_recipes(db_session, "u1")
    
    assert len(recipes) == 1
    r_data = recipes[0]
    assert r_data['recipe'].id == "R_POTION"
    assert r_data['can_craft'] is False
    assert "Herb x1" in r_data['missing'][0] # Need 2, have 1, missing 1

@pytest.mark.asyncio
async def test_craft_item_success(db_session):
    # Setup Data
    # Items
    metal = Item(id="METAL", name="Metal Scrap")
    sword = Item(id="SWORD", name="Iron Sword")
    db_session.add_all([metal, sword])
    
    # Recipe: 3 Metal -> 1 Sword
    recipe = Recipe(id="R_SWORD", name="Forge Sword", result_item_id="SWORD", result_quantity=1)
    db_session.add(recipe)
    await db_session.commit()
    
    ing = RecipeIngredient(recipe_id="R_SWORD", item_id="METAL", quantity_required=3)
    db_session.add(ing)
    
    # User with 5 Metal (Enough)
    u_item = UserItem(user_id="u2", item_id="METAL", quantity=5)
    db_session.add(u_item)
    await db_session.commit()
    
    # Action
    res = await crafting_service.craft_item(db_session, "u2", "R_SWORD")
    
    assert res["success"] is True
    
    # Check Ingredients Consumed
    await db_session.refresh(u_item)
    assert u_item.quantity == 2 # 5 - 3 = 2
    
    # Check Result Item
    stmt = select(UserItem).where(UserItem.user_id == "u2", UserItem.item_id == "SWORD")
    result = await db_session.execute(stmt)
    sword_inv = result.scalars().first()
    assert sword_inv is not None
    assert sword_inv.quantity == 1
