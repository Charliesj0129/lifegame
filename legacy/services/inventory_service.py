from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from legacy.models.gamification import Item, UserItem, UserBuff
from app.models.user import User
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)


class InventoryService:
    async def get_user_inventory(self, session: AsyncSession, user_id: str):
        from sqlalchemy.orm import joinedload

        stmt = (
            select(UserItem)
            .where(UserItem.user_id == user_id)
            .options(joinedload(UserItem.item))
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_active_buffs(self, session: AsyncSession, user_id: str):
        now = datetime.now(timezone.utc)
        stmt = select(UserBuff).where(
            UserBuff.user_id == user_id, UserBuff.expires_at > now
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def use_item(
        self, session: AsyncSession, user_id: str, item_keyword: str
    ) -> str:
        # Find item in inventory (by partial name match or exact ID?)
        # For chat bot, exact ID is hard. Let's try name match join.
        stmt = (
            select(UserItem)
            .join(Item)
            .where(
                UserItem.user_id == user_id,
                UserItem.quantity > 0,
                Item.name.ilike(f"%{item_keyword}%"),
            )
        )
        result = await session.execute(stmt)
        user_item = result.scalars().first()

        if not user_item:
            return f"背包中沒有符合「{item_keyword}」的道具。"

        item = await session.get(Item, user_item.item_id)
        if not item or not item.effect_meta:
            return f"{item.name if item else '道具'}無法使用。"

        meta = item.effect_meta or {}
        effect = meta.get("effect")
        # {"buff": "INT", "multiplier": 1.2, "duration_minutes": 60}

        if item.id == "ITEM_DATA_SHARD" or effect == "lore_unlock":
            from legacy.services.lore_service import lore_service

            entry = await lore_service.unlock_data_shard(session, user_id)

            user_item.quantity -= 1
            if user_item.quantity <= 0:
                await session.delete(user_item)

            await session.commit()
            return entry

        if "buff" in meta or effect == "buff_multiplier":
            # Create Buff
            duration = meta.get("duration_minutes", 60)
            multiplier = meta.get("multiplier", 1.1)
            target = (
                meta.get("buff")
                or meta.get("attribute")
                or meta.get("target_attribute")
                or "ALL"
            )

            expires = datetime.now(timezone.utc) + timedelta(minutes=duration)

            buff = UserBuff(
                user_id=user_id,
                target_attribute=target,
                multiplier=multiplier,
                expires_at=expires,
            )
            session.add(buff)

            # Consume
            user_item.quantity -= 1
            if user_item.quantity <= 0:
                await session.delete(user_item)  # Remove 0 quantity rows?

            await session.commit()
            return f"已使用 {item.name}！{target} 效果提升 {multiplier} 倍，持續 {duration} 分鐘。"

        if effect == "restore_hp":
            amount = int(meta.get("amount", 0))
            if amount <= 0:
                return f"使用 {item.name} 但沒有任何效果。"
            user = await session.get(User, user_id)
            if not user:
                return "找不到使用者。"
            from legacy.services.hp_service import hp_service

            await hp_service.apply_hp_change(
                session, user, amount, source="item_restore_hp"
            )

            user_item.quantity -= 1
            if user_item.quantity <= 0:
                await session.delete(user_item)
            await session.commit()
            return f"已使用 {item.name}！HP +{amount}。"

        if effect == "grant_xp":
            amount = int(meta.get("amount", 0))
            if amount <= 0:
                return f"使用 {item.name} 但沒有任何效果。"

            user = await session.get(User, user_id)
            if not user:
                return "找不到使用者。"

            user.xp = (user.xp or 0) + amount

            user_item.quantity -= 1
            if user_item.quantity <= 0:
                await session.delete(user_item)

            await session.commit()
            return f"已使用 {item.name}！XP +{amount}。"

        return f"使用 {item.name} 但沒有任何效果。"


inventory_service = InventoryService()
