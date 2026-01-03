from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from app.models.gamification import Item, UserItem, UserBuff
from app.models.user import User
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class InventoryService:
    async def get_user_inventory(self, session: AsyncSession, user_id: str):
        from sqlalchemy.orm import joinedload
        stmt = select(UserItem).where(UserItem.user_id == user_id).options(joinedload(UserItem.item))
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_active_buffs(self, session: AsyncSession, user_id: str):
        now = datetime.now()
        stmt = select(UserBuff).where(
            UserBuff.user_id == user_id, 
            UserBuff.expires_at > now
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def use_item(self, session: AsyncSession, user_id: str, item_keyword: str) -> str:
        # Find item in inventory (by partial name match or exact ID?)
        # For chat bot, exact ID is hard. Let's try name match join.
        stmt = select(UserItem).join(Item).where(
            UserItem.user_id == user_id,
            UserItem.quantity > 0,
            Item.name.ilike(f"%{item_keyword}%")
        )
        result = await session.execute(stmt)
        user_item = result.scalars().first()

        if not user_item:
            return f"You don't have any item matching '{item_keyword}'."
        
        item = await session.get(Item, user_item.item_id)
        if not item or not item.effect_meta:
            return f"{item.name if item else 'Item'} cannot be used."

        meta = item.effect_meta
        # {"buff": "INT", "multiplier": 1.2, "duration_minutes": 60}
        
        if "buff" in meta:
            # Create Buff
            duration = meta.get("duration_minutes", 60)
            multiplier = meta.get("multiplier", 1.1)
            target = meta.get("buff", "ALL")
            
            expires = datetime.now() + timedelta(minutes=duration)
            
            buff = UserBuff(
                user_id=user_id,
                target_attribute=target,
                multiplier=multiplier,
                expires_at=expires
            )
            session.add(buff)
            
            # Consume
            user_item.quantity -= 1
            if user_item.quantity == 0:
                await session.delete(user_item) # Remove 0 quantity rows?
            
            await session.commit()
            return f"Used {item.name}! applied {multiplier}x {target} Boost for {duration}m."
        else:
             return f"Used {item.name}, but nothing happened?"

inventory_service = InventoryService()
