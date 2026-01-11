from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from legacy.models.gamification import UserItem, Recipe, RecipeIngredient
import random


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
                if user_qty < ing.quantity_required:
                    can_craft = False
                    missing.append(f"{ing.item.name} x{ing.quantity_required - user_qty}")

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
            if not ui or ui.quantity < ing.quantity_required:
                return {
                    "success": False,
                    "message": f"素材不足，無法合成 {recipe.name}。",
                }

        # 3. Consume Ingredients (always consumed on attempt)
        for ing in recipe.ingredients:
            ui = user_items.get(ing.item_id)
            ui.quantity -= ing.quantity_required
            if ui.quantity == 0:
                await session.delete(ui)

        success_rate = float(getattr(recipe, "success_rate", 1.0) or 1.0)
        is_success = random.random() <= success_rate

        if not is_success:
            await session.commit()
            return {"success": False, "message": "💥 實驗失敗！素材化為灰燼。"}

        # 4. Add Result Item
        result_ui = user_items.get(recipe.result_item_id)
        if result_ui:
            result_ui.quantity += recipe.result_quantity
        else:
            new_item = UserItem(
                user_id=user_id,
                item_id=recipe.result_item_id,
                quantity=recipe.result_quantity,
            )
            session.add(new_item)

        await session.commit()
        return {"success": True, "message": f"⚒️ 合成成功！獲得 {recipe.name}。"}


crafting_service = CraftingService()
