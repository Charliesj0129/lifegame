import uuid
from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import Item, ItemRarity, ItemType, UserItem
from app.models.user import User


class InventoryService:
    async def get_inventory(self, session: AsyncSession, user_id: str) -> List[Tuple[Item, int]]:
        """
        Returns a list of (Item, quantity) tuples for the user.
        """
        # UserItem already has relationship to Item, but we want to return (Item, qty) format for renderer
        stmt = select(UserItem, Item).join(Item, UserItem.item_id == Item.id).where(UserItem.user_id == user_id)
        result = await session.execute(stmt)
        rows = result.all()
        # rows are [(UserItem, Item), ...]
        return [(row[1], row[0].quantity) for row in rows]

    async def get_user_inventory(self, session: AsyncSession, user_id: str) -> List[Tuple[Item, int]]:
        """Alias for get_inventory to match Type Callers"""
        return await self.get_inventory(session, user_id)

    async def add_item(self, session: AsyncSession, user_id: str, item_id: str, quantity: int = 1):
        """
        Adds an item to the user's inventory.
        """
        # Check if slot exists
        stmt = select(UserItem).where(UserItem.user_id == user_id, UserItem.item_id == item_id)
        slot = (await session.execute(stmt)).scalars().first()

        if slot:
            slot.quantity += quantity
        else:
            slot = UserItem(user_id=user_id, item_id=item_id, quantity=quantity)
            session.add(slot)

        await session.commit()

    async def remove_item(self, session: AsyncSession, user_id: str, item_id: str, quantity: int = 1) -> bool:
        """
        Removes an item. Returns False if insufficient quantity.
        """
        stmt = select(UserItem).where(UserItem.user_id == user_id, UserItem.item_id == item_id)
        slot = (await session.execute(stmt)).scalars().first()

        if not slot or slot.quantity < quantity:
            return False

        slot.quantity -= quantity
        if slot.quantity <= 0:
            await session.delete(slot)

        await session.commit()
        return True

    async def use_item(self, session: AsyncSession, user_id: str, item_id: str) -> bool:
        """
        Consumes a consumable item.
        """
        stmt = select(UserItem).where(UserItem.user_id == user_id, UserItem.item_id == item_id)
        slot = (await session.execute(stmt)).scalars().first()

        if not slot or slot.quantity < 1:
            return False

        # TODO: Apply Item Effect logic here (Strategy Pattern)
        # For now, just decrement
        return await self.remove_item(session, user_id, item_id, 1)

    async def equip_item(self, session: AsyncSession, user_id: str, item_id: str) -> bool:
        """
        Equips an equipment item.
        """
        # Placeholder for equipment logic
        return True

    async def seed_default_items_if_needed(self, session: AsyncSession):
        """
        Seeds basic game items if the Item table is empty.
        """
        stmt = select(Item).limit(1)
        existing = (await session.execute(stmt)).scalars().first()
        if existing:
            return

        items = [
            Item(
                id=str(uuid.uuid4()),
                name="生命藥水",
                description="恢復 50 點生命值。",
                type=ItemType.CONSUMABLE,
                rarity=ItemRarity.COMMON,
                effect_meta={"hp_restore": 50},
                price=50,
            ),
            Item(
                id=str(uuid.uuid4()),
                name="經驗秘典 (小)",
                description="獲得 100 點經驗值。",
                type=ItemType.CONSUMABLE,
                rarity=ItemRarity.UNCOMMON,
                effect_meta={"xp_grant": 100},
                price=150,
            ),
            Item(
                id=str(uuid.uuid4()),
                name="專注藥劑",
                description="提升專注力，接下來的任務 XP +20%。",
                type=ItemType.CONSUMABLE,
                rarity=ItemRarity.RARE,
                effect_meta={"buff": "focus", "duration": 3600},
                price=300,
            ),
            Item(
                id=str(uuid.uuid4()),
                name="命運硬幣",
                description="重新生成今日任務 (Reroll)。",
                type=ItemType.CONSUMABLE,
                rarity=ItemRarity.EPIC,
                effect_meta={"action": "reroll_quest"},
                price=500,
            ),
        ]
        session.add_all(items)
        await session.commit()

    async def get_active_buffs(self, session: AsyncSession, user_id: str):
        """
        Returns active buffs affecting XP/loot. Placeholder for now (no buffs system wired).
        """
        return []


inventory_service = InventoryService()
