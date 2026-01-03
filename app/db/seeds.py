import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.gamification import Item, ItemRarity, ItemType

initial_items = [
    Item(
        id="POTION_XP_S",
        name="Small XP Potion",
        description="Grants 50 XP instantly.",
        rarity=ItemRarity.COMMON,
        type=ItemType.CONSUMABLE,
        effect_meta={"effect": "grant_xp", "amount": 50}
    ),
    Item(
        id="POTION_FOCUS",
        name="Focus Potion",
        description="Deep Work (INT) grants +50% XP for 2 hours.",
        rarity=ItemRarity.UNCOMMON,
        type=ItemType.CONSUMABLE,
        effect_meta={"effect": "buff_multiplier", "attribute": "INT", "multiplier": 1.5, "duration_minutes": 120}
    ),
    Item(
        id="COUPON_COFFEE",
        name="Coffee Fund",
        description="Redeem for 1 Free Coffee.",
        rarity=ItemRarity.RARE,
        type=ItemType.REWARD,
        effect_meta={"effect": "redeem_o2o"}
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

if __name__ == "__main__":
    asyncio.run(seed_items())
