import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.gamification import Item, ItemRarity, ItemType, Recipe, RecipeIngredient

initial_items = [
    Item(
        id="POTION_XP_S",
        name="小型經驗藥水",
        description="立即獲得 50 點經驗。",
        rarity=ItemRarity.COMMON,
        type=ItemType.CONSUMABLE,
        price=80,
        is_purchasable=False,
        effect_meta={"effect": "grant_xp", "amount": 50}
    ),
    Item(
        id="POTION_FOCUS",
        name="專注藥水",
        description="智力任務經驗 +50%（2 小時）。",
        rarity=ItemRarity.UNCOMMON,
        type=ItemType.CONSUMABLE,
        price=150,
        is_purchasable=False,
        effect_meta={"effect": "buff_multiplier", "attribute": "INT", "multiplier": 1.5, "duration_minutes": 120}
    ),
    Item(
        id="COUPON_COFFEE",
        name="咖啡基金",
        description="可兌換一杯咖啡。",
        rarity=ItemRarity.RARE,
        type=ItemType.REWARD,
        price=300,
        is_purchasable=False,
        effect_meta={"effect": "redeem_o2o"}
    ),
    Item(
        id="ITEM_DATA_SHARD",
        name="加密數據磁碟",
        description="解鎖一段 Lore 碎片。",
        rarity=ItemRarity.RARE,
        type=ItemType.KEY,
        price=250,
        is_purchasable=False,
        effect_meta={"effect": "lore_unlock"}
    ),
    Item(
        id="ITEM_REDEMPTION_TICKET",
        name="贖罪券",
        description="立即解除一次懲罰狀態。",
        rarity=ItemRarity.UNCOMMON,
        type=ItemType.CONSUMABLE,
        price=300,
        is_purchasable=False,
        effect_meta={"effect": "clear_penalty"}
    ),
    Item(
        id="POTION_VITAL_S",
        name="體力修復藥水",
        description="立即恢復 10 點生命值。",
        rarity=ItemRarity.COMMON,
        type=ItemType.CONSUMABLE,
        price=90,
        is_purchasable=False,
        effect_meta={"effect": "restore_hp", "amount": 10}
    ),
    Item(
        id="MAT_HERB",
        name="草本材料",
        description="常見的藥草素材。",
        rarity=ItemRarity.COMMON,
        type=ItemType.KEY,
        price=40,
        is_purchasable=False,
        effect_meta={}
    ),
    Item(
        id="MAT_METAL",
        name="金屬碎片",
        description="可用於基礎合成。",
        rarity=ItemRarity.COMMON,
        type=ItemType.KEY,
        price=50,
        is_purchasable=False,
        effect_meta={}
    )
]

async def seed_items():
    async with AsyncSessionLocal() as session:
        for item in initial_items:
            existing = await session.get(Item, item.id)
            if not existing:
                print(f"Seeding item: {item.name}")
                session.add(item)
            else:
                print(f"Item exists: {item.name}")
        await session.commit()


async def seed_recipes():
    async with AsyncSessionLocal() as session:
        recipes = [
            Recipe(
                id="RECIPE_FOCUS_POTION",
                name="專注藥水配方",
                result_item_id="POTION_FOCUS",
                result_quantity=1,
                success_rate=0.9
            ),
            Recipe(
                id="RECIPE_VITAL_POTION",
                name="體力修復藥水配方",
                result_item_id="POTION_VITAL_S",
                result_quantity=1,
                success_rate=1.0
            ),
        ]

        for recipe in recipes:
            existing = await session.get(Recipe, recipe.id)
            if not existing:
                session.add(recipe)

        ingredients = [
            RecipeIngredient(recipe_id="RECIPE_FOCUS_POTION", item_id="MAT_HERB", quantity_required=2),
            RecipeIngredient(recipe_id="RECIPE_FOCUS_POTION", item_id="MAT_METAL", quantity_required=1),
            RecipeIngredient(recipe_id="RECIPE_VITAL_POTION", item_id="MAT_HERB", quantity_required=1),
        ]

        for ing in ingredients:
            session.add(ing)

        await session.commit()

if __name__ == "__main__":
    asyncio.run(seed_items())
    asyncio.run(seed_recipes())
