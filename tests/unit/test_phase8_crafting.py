import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.base import Base
from legacy.models.gamification import Item, UserItem, Recipe, RecipeIngredient
from legacy.services.crafting_service import crafting_service
from legacy.services.inventory_service import inventory_service


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
async def test_crafting_flow(db_session):
    user_id = "test_user_craft"

    # 1. Seed Recipes & Items
    await inventory_service.seed_default_items_if_needed(db_session)
    await crafting_service.seed_default_recipes(db_session)

    # Verify Recipe exists
    from sqlalchemy.orm import selectinload

    stmt = select(Recipe).options(selectinload(Recipe.ingredients))
    recipe = (await db_session.execute(stmt)).scalars().first()
    assert recipe is not None
    assert "大生命" in recipe.name

    # Verify Ingredients need Potion
    ing = recipe.ingredients[0]
    required_qty = ing.quantity_required

    # 2. Check Available Recipes (Should be 0 craftable)
    available = await crafting_service.get_available_recipes(db_session, user_id)
    assert available[0]["can_craft"] is False

    # 3. Add Ingredients to User (Add 3 Potions)
    await inventory_service.add_item(db_session, user_id, ing.item_id, required_qty)

    # 4. Check Available Recipes (Should be craftable)
    available = await crafting_service.get_available_recipes(db_session, user_id)
    assert available[0]["can_craft"] is True

    # 5. Execute Craft
    import unittest.mock

    with unittest.mock.patch("legacy.services.crafting_service.random.random", return_value=0.0):
        res = await crafting_service.craft_item(db_session, user_id, recipe.id)

    assert res["success"] is True
    assert "獲得" in res["message"]

    # 6. Verify result
    # Ingredients consumed?
    inv = await inventory_service.get_inventory(db_session, user_id)
    # Result item (Mega Potion) should be present
    mega_pot = next((i for i, q in inv if i.id == recipe.result_item_id), None)
    assert mega_pot is not None

    # Ingredients should be gone (if exact amount used)
    # Check potion quantity
    potion_inv = next((q for i, q in inv if i.id == ing.item_id), 0)
    assert potion_inv == 0
