from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from legacy.models.gamification import Item, ItemRarity, ItemType
import logging

logger = logging.getLogger(__name__)


async def seed_shop_items(session: AsyncSession):
    """Seed initial shop items if they don't exist."""
    items_data = [
        {
            "id": "potion_hp_small",
            "name": "小型治療藥水",
            "description": "恢復 30 點生命值。",
            "price": 50,
            "rarity": ItemRarity.COMMON,
            "type": ItemType.CONSUMABLE,
            "is_purchasable": True,
            "effect_meta": {"effect": "restore_hp", "value": 30},
        },
        {
            "id": "potion_hp_large",
            "name": "強力治療藥水",
            "description": "恢復 80 點生命值。",
            "price": 120,
            "rarity": ItemRarity.UNCOMMON,
            "type": ItemType.CONSUMABLE,
            "is_purchasable": True,
            "effect_meta": {"effect": "restore_hp", "value": 80},
        },
        {
            "id": "clear_penalty",
            "name": "贖罪卷軸",
            "description": "消除當前的懲罰狀態。",
            "price": 200,
            "rarity": ItemRarity.RARE,
            "type": ItemType.CONSUMABLE,
            "is_purchasable": True,
            "effect_meta": {"effect": "clear_penalty"},
        },
        {
            "id": "xp_tome_1",
            "name": "戰鬥手冊",
            "description": "獲得 100 點經驗值。",
            "price": 300,
            "rarity": ItemRarity.RARE,
            "type": ItemType.CONSUMABLE,
            "is_purchasable": True,
            "effect_meta": {"effect": "grant_xp", "value": 100},
        },
    ]

    try:
        for item_dict in items_data:
            stmt = select(Item).where(Item.id == item_dict["id"])
            result = await session.execute(stmt)
            existing = result.scalars().first()

            if not existing:
                item = Item(**item_dict)
                session.add(item)
                logger.info(f"Seeding new item: {item.name}")
            else:
                # Update properties if needed, or skip
                existing.name = item_dict["name"]  # Ensure name update
                existing.price = item_dict["price"]
                existing.is_purchasable = True
                session.add(existing)

        await session.commit()
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        await session.rollback()
