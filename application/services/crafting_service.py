import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.gamification import Recipe, RecipeIngredient, UserItem


class CraftingService:
    async def get_available_recipes(self, session: AsyncSession, user_id: str):
        # Fetch all recipes with ingredients and result item
        stmt = select(Recipe).options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.item),
            selectinload(Recipe.result_item),
        )
        result = await session.execute(stmt)
        recipes = result.scalars().all()

        # Fetch User Inventory
        stmt_inv = select(UserItem).where(UserItem.user_id == user_id)
        result_inv = await session.execute(stmt_inv)
        inventory = {ui.item_id: ui.quantity for ui in result_inv.scalars().all()}

        craftable_recipes = []
        for r in recipes:
            can_craft = True
            missing = []
            for ing in r.ingredients:
                user_qty = inventory.get(ing.item_id, 0)
                if (user_qty or 0) < (ing.quantity_required or 0):
                    can_craft = False
                    missing.append(f"{ing.item.name} x{(ing.quantity_required or 0) - (user_qty or 0)}")

            craftable_recipes.append({"recipe": r, "can_craft": can_craft, "missing": missing})

        return craftable_recipes

    async def craft_item(self, session: AsyncSession, user_id: str, recipe_id: str):
        # 1. Fetch Recipe
        stmt = select(Recipe).where(Recipe.id == recipe_id).options(selectinload(Recipe.ingredients))
        result = await session.execute(stmt)
        recipe = result.scalars().first()

        if not recipe:
            return {"success": False, "message": "找不到配方。"}

        # 2. Check Ingredients
        stmt_inv = select(UserItem).where(UserItem.user_id == user_id)
        result_inv = await session.execute(stmt_inv)
        user_items = {ui.item_id: ui for ui in result_inv.scalars().all()}

        for ing in recipe.ingredients:
            ui = user_items.get(ing.item_id)
            # Check safely
            if not ui or (ui.quantity or 0) < (ing.quantity_required or 0):
                return {
                    "success": False,
                    "message": f"素材不足，無法合成 {recipe.name}。",
                }

        # 3. Consume Ingredients (always consumed on attempt)
        for ing in recipe.ingredients:
            ui = user_items.get(ing.item_id)
            if ui:  # Safety check for MyPy
                ui.quantity = (ui.quantity or 0) - (ing.quantity_required or 0)
                if ui.quantity <= 0:
                    await session.delete(ui)

        success_rate = float(getattr(recipe, "success_rate", 1.0) or 1.0)
        is_success = random.random() <= success_rate

        if not is_success:
            await session.commit()
            return {"success": False, "message": "💥 實驗失敗！素材化為灰燼。"}

        # 4. Add Result Item
        result_ui = user_items.get(recipe.result_item_id)
        if result_ui:
            result_ui.quantity = (result_ui.quantity or 0) + (recipe.result_quantity or 1)
        else:
            new_item = UserItem(
                user_id=user_id,
                item_id=recipe.result_item_id,
                quantity=recipe.result_quantity,
            )
            session.add(new_item)

        await session.commit()
        await session.commit()

        # --- Graph Sync ---
        # --- Graph Sync ---
        # --- Graph Sync ---
        try:
            from app.core.container import container

            adapter = container.graph_service.adapter

            if adapter:
                # Ensure Item Node
                adapter.add_node("Item", {"id": recipe.result_item_id, "name": recipe.name})

                # Link User -> Item (CRAFTED)
                import datetime

                await adapter.add_relationship(
                    "User",
                    user_id,
                    "CRAFTED",
                    "Item",
                    str(recipe.result_item_id),
                    {"timestamp": datetime.datetime.now().isoformat()},
                    from_key_field="id",
                    to_key_field="id",
                )
        except Exception as e:
            # Non-blocking
            print(f"Graph Sync Failed: {e}")

        return {"success": True, "message": f"⚒️ 合成成功！獲得 {recipe.name}。"}

    async def seed_default_recipes(self, session: AsyncSession):
        """
        Seeds basic recipes if none exist.
        """
        stmt = select(Recipe).limit(1)
        existing = (await session.execute(stmt)).scalars().first()
        if existing:
            return

        # Fetch basic items to link
        from app.models.gamification import Item

        items = (await session.execute(select(Item))).scalars().all()
        item_map = {i.name: i.id for i in items}

        # We need "Life Potion" (生命藥水) -> "Mega Potion" (大生命藥水) or something
        # Let's assume we have "生命藥水".
        # Let's create a "Mega Potion" item if not exists
        mega_potion_id = "ITEM_MEGA_POTION"
        mega_potion = await session.get(Item, mega_potion_id)
        if not mega_potion:
            mega_potion = Item(
                id=mega_potion_id,
                name="大生命藥水",
                description="恢復 200 點生命值。",
                type="CONSUMABLE",
                rarity="RARE",
                effect_meta={"hp_restore": 200},
                price=300,
            )
            session.add(mega_potion)

        # Recipe: 3x Potion -> 1x Mega Potion
        potion_id = item_map.get("生命藥水")
        if potion_id:
            recipe = Recipe(
                id="RECIPE_MEGA_POTION",
                name="合成大生命藥水",
                result_item_id=mega_potion_id,
                result_quantity=1,
                success_rate=0.9,
            )
            session.add(recipe)
            await session.flush()

            ingredient = RecipeIngredient(recipe_id=recipe.id, item_id=potion_id, quantity_required=3)
            session.add(ingredient)
            await session.commit()


crafting_service = CraftingService()
