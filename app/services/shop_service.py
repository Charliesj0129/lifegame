from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.gamification import Item, UserItem
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

class ShopService:
    async def list_shop_items(self, session: AsyncSession):
        stmt = select(Item).where(Item.is_purchasable == True)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def buy_item(self, session: AsyncSession, user_id: str, item_id: str):
        # 1. Fetch User and Item
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalars().first()
        
        item = await session.get(Item, item_id)
        
        if not user:
            return {"success": False, "message": "User not found."}
        if not item:
            return {"success": False, "message": "Item not found."}
        if not item.is_purchasable:
            return {"success": False, "message": "This item is not for sale."}
        
        # 2. Check Funds
        price = item.price or 0
        if user.gold < price:
            return {"success": False, "message": f"Insufficient funds. Need {price} Gold."}
        
        # 3. Transact
        user.gold -= price
        
        # 4. Add to Inventory
        stmt_inv = select(UserItem).where(UserItem.user_id == user_id, UserItem.item_id == item_id)
        result_inv = await session.execute(stmt_inv)
        user_item = result_inv.scalars().first()
        
        if user_item:
            user_item.quantity += 1
        else:
            user_item = UserItem(user_id=user_id, item_id=item_id, quantity=1)
            session.add(user_item)
            
        await session.commit()
        return {"success": True, "message": f"Purchased {item.name} for {price} Gold."}

shop_service = ShopService()
