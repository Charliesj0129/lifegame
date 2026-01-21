import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import Item, UserItem
from app.models.user import User

logger = logging.getLogger(__name__)


class ShopService:
    async def list_shop_items(self, session: AsyncSession):
        stmt = select(Item).where(Item.is_purchasable)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def generate_shop_items(self, session: AsyncSession, user_id: str, goal_tags: list[str] | None = None):
        # 1. Fetch User and Item (With Locking)
        # Use with_for_update() to prevent Double Spend race conditions
        stmt = select(User).where(User.id == user_id).with_for_update()
        result = await session.execute(stmt)
        _ = result.scalars().first()

    async def buy_item(self, session: AsyncSession, user_id: str, item_id: str):
        # 1. Fetch User and Item (With Locking)
        # Use with_for_update() to prevent Double Spend race conditions
        stmt = select(User).where(User.id == user_id).with_for_update()
        result = await session.execute(stmt)
        user = result.scalars().first()

        item = await session.get(Item, item_id)

        if not user:
            return {"success": False, "message": "找不到使用者。"}
        if not item:
            return {"success": False, "message": "找不到商品。"}
        if not item.is_purchasable:
            return {"success": False, "message": "此商品不可購買。"}

        # 2. Check Funds
        price = item.price or 0
        if user.gold < price:
            return {"success": False, "message": f"金幣不足，需要 {price} G。"}

        # 3. Transact
        user.gold -= price

        # 4. Add to Inventory (or apply instant effect)
        effect = (item.effect_meta or {}).get("effect")
        if effect == "clear_penalty":
            user.penalty_pending = False
            session.add(user)
        stmt_inv = select(UserItem).where(UserItem.user_id == user_id, UserItem.item_id == item_id)
        result_inv = await session.execute(stmt_inv)
        user_item = result_inv.scalars().first()

        if user_item:
            user_item.quantity += 1
        else:
            user_item = UserItem(user_id=user_id, item_id=item_id, quantity=1)
            session.add(user_item)

        await session.commit()

        # F3: NPC Interaction (Kael)
        from application.services.npc_service import npc_service

        kael_context = {"item_bought": item.name, "cost": price, "user_gold_left": user.gold}
        dialogue = await npc_service.get_dialogue("kael", f"User bought {item.name} for {price}G.", kael_context)

        return {"success": True, "message": f"{dialogue}\n\n[系統] 已購買 {item.name}（-{price} G）。"}

    async def refresh_daily_stock(
        self, session: AsyncSession, slots: int = 3, user_hp: int = 100, goal_tags: list = None
    ):
        """
        F7: Context-Aware Shop Refresh.
        Weights item selection based on user state (HP, Goals).
        """
        from app.models.gamification import ItemRarity

        result = await session.execute(select(Item))
        items = result.scalars().all()
        if not items:
            return []

        for item in items:
            item.is_purchasable = False
            session.add(item)

        import random

        # Context-aware filtering
        prioritized = []

        # If HP is low, prioritize healing items
        if user_hp < 30:
            healing_items = [i for i in items if "heal" in (i.effect_meta or {}).get("effect", "").lower()]
            prioritized.extend(healing_items)

        # If user has goal tags, prioritize related items
        if goal_tags:
            for item in items:
                item_tags = (item.effect_meta or {}).get("tags", [])
                if any(gt.lower() in str(item_tags).lower() for gt in goal_tags):
                    if item not in prioritized:
                        prioritized.append(item)

        rare_pool = [i for i in items if i.rarity in {ItemRarity.RARE, ItemRarity.EPIC, ItemRarity.LEGENDARY}]

        selected = []

        # Add prioritized items first
        for item in prioritized[:2]:
            if item not in selected:
                selected.append(item)

        # Add one rare if available
        if rare_pool:
            rare_choice = random.choice(rare_pool)
            if rare_choice not in selected:
                selected.append(rare_choice)

        # Fill remaining slots
        remaining = [i for i in items if i not in selected]
        random.shuffle(remaining)
        while remaining and len(selected) < slots:
            selected.append(remaining.pop())

        for item in selected[:slots]:
            item.is_purchasable = True
            session.add(item)

        await session.commit()
        await session.commit()
        return selected[:slots]

    async def get_daily_stock(self, session: AsyncSession, user_id: str) -> list[Item]:
        """
        Returns current stock. Actually just list_shop_items for now,
        or we could check if daily generation is needed.
        """
        # For simplicity in MVP, we just list purchasable items as stock
        return await self.list_shop_items(session)


shop_service = ShopService()
