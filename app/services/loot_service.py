import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql.expression import func
from app.models.gamification import Item, ItemRarity, UserItem


class LootService:
    def __init__(self):
        self.base_drop_rate = 0.20
        self.rarity_weights = {
            ItemRarity.COMMON: 60,
            ItemRarity.UNCOMMON: 30,
            ItemRarity.RARE: 8,
            ItemRarity.EPIC: 1.9,
            ItemRarity.LEGENDARY: 0.1,
        }

        # Difficulty multipliers (from Rules)
        self.diff_multipliers = {
            "F": 0.5,
            "E": 1.0,
            "D": 1.2,  # slight boost
            "C": 1.5,
            "B": 2.0,
            "A": 3.0,
        }

    def _roll_for_drop(self, difficulty: str) -> bool:
        multiplier = self.diff_multipliers.get(difficulty, 1.0)
        chance = self.base_drop_rate * multiplier
        # Cap at 100%
        if chance > 1.0:
            chance = 1.0
        return random.random() < chance

    def _select_rarity(self) -> ItemRarity:
        # Weighted random choice
        rarities = list(self.rarity_weights.keys())
        weights = list(self.rarity_weights.values())
        return random.choices(rarities, weights=weights, k=1)[0]

    async def calculate_drop(
        self, session: AsyncSession, difficulty: str, force_drop: bool = False
    ) -> Item | None:
        if not force_drop and not self._roll_for_drop(difficulty):
            return None

        target_rarity = self._select_rarity()

        # Fetch items of this rarity
        # In production this should be cached. MVP: Query DB.
        result = await session.execute(
            select(Item)
            .where(Item.rarity == target_rarity)
            .order_by(func.random())
            .limit(1)
        )
        item = result.scalars().first()

        # Fallback if no item of that rarity exists (e.g. Legendary not seeded yet)
        if not item:
            # Fallback to Common
            result = await session.execute(
                select(Item)
                .where(Item.rarity == ItemRarity.COMMON)
                .order_by(func.random())
                .limit(1)
            )
            item = result.scalars().first()

        return item

    async def grant_item(
        self, session: AsyncSession, user_id: str, item: Item
    ) -> UserItem:
        # Check if user already has item
        result = await session.execute(
            select(UserItem).where(
                UserItem.user_id == user_id, UserItem.item_id == item.id
            )
        )
        user_item = result.scalars().first()

        if user_item:
            user_item.quantity += 1
        else:
            user_item = UserItem(user_id=user_id, item_id=item.id, quantity=1)
            session.add(user_item)

        await session.commit()
        await session.refresh(user_item)
        return user_item

    async def grant_guaranteed_drop(
        self,
        session: AsyncSession,
        user_id: str,
        min_rarity: ItemRarity = ItemRarity.RARE,
    ) -> Item | None:
        order = [
            ItemRarity.COMMON,
            ItemRarity.UNCOMMON,
            ItemRarity.RARE,
            ItemRarity.EPIC,
            ItemRarity.LEGENDARY,
        ]
        try:
            min_index = order.index(min_rarity)
        except ValueError:
            min_index = order.index(ItemRarity.RARE)

        eligible = order[min_index:]
        result = await session.execute(
            select(Item)
            .where(Item.rarity.in_(eligible))
            .order_by(func.random())
            .limit(1)
        )
        item = result.scalars().first()
        if not item:
            return None
        await self.grant_item(session, user_id, item)
        return item


loot_service = LootService()
