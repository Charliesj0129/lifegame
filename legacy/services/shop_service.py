from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from legacy.models.gamification import Item, UserItem
from app.models.user import User
import logging

logger = logging.getLogger(__name__)


class ShopService:
    async def list_shop_items(self, session: AsyncSession):
        stmt = select(Item).where(Item.is_purchasable)
        result = await session.execute(stmt)
        return result.scalars().all()

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
        return {"success": True, "message": f"已購買 {item.name}（-{price} G）。"}

    async def refresh_daily_stock(self, session: AsyncSession, slots: int = 3):
        from legacy.models.gamification import ItemRarity

        result = await session.execute(select(Item))
        items = result.scalars().all()
        if not items:
            return []

        for item in items:
            item.is_purchasable = False
            session.add(item)

        import random

        rare_pool = [i for i in items if i.rarity in {ItemRarity.RARE, ItemRarity.EPIC, ItemRarity.LEGENDARY}]
        [i for i in items if i not in rare_pool]

        selected = []
        if rare_pool:
            selected.append(random.choice(rare_pool))
        remaining = [i for i in items if i not in selected]
        random.shuffle(remaining)
        while remaining and len(selected) < slots:
            selected.append(remaining.pop())

        for item in selected[:slots]:
            item.is_purchasable = True
            session.add(item)

        await session.commit()
        return selected[:slots]


shop_service = ShopService()
