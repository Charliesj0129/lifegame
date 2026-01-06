import datetime
import enum
import logging
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.quest import Quest, QuestStatus

logger = logging.getLogger(__name__)


class HPStatus(str, enum.Enum):
    HEALTHY = "HEALTHY"
    CRITICAL = "CRITICAL"
    HOLLOWED = "HOLLOWED"
    RECOVERING = "RECOVERING"


class HPService:
    STATUS_HEALTHY = HPStatus.HEALTHY.value
    STATUS_CRITICAL = HPStatus.CRITICAL.value
    STATUS_HOLLOWED = HPStatus.HOLLOWED.value
    STATUS_RECOVERING = HPStatus.RECOVERING.value

    HP_RECOVERY_BY_DIFF = {
        "S": 25,
        "A": 20,
        "B": 18,
        "C": 20,
        "D": 10,
        "E": 6,
        "F": 3,
    }

    def _status_from_hp(self, hp_value: int) -> str:
        if hp_value <= 0:
            return self.STATUS_HOLLOWED
        if hp_value < 30:
            return self.STATUS_CRITICAL
        return self.STATUS_HEALTHY

    async def apply_hp_change(
        self,
        session: AsyncSession,
        user: User,
        delta: int,
        source: str = "",
        commit: bool = True,
        trigger_rescue: bool = False,
    ) -> User:
        was_hollowed = user.is_hollowed or user.hp_status == self.STATUS_HOLLOWED
        max_hp = user.max_hp or 100
        new_hp = max(0, min(max_hp, (user.hp or 0) + delta))
        new_status = self._status_from_hp(new_hp)
        if was_hollowed and new_status != self.STATUS_HOLLOWED:
            new_status = self.STATUS_RECOVERING
        user.hp = new_hp
        user.hp_status = new_status
        user.is_hollowed = user.hp_status == self.STATUS_HOLLOWED
        if user.is_hollowed and not user.hollowed_at:
            user.hollowed_at = datetime.datetime.now(datetime.timezone.utc)
        if not user.is_hollowed and user.hollowed_at:
            user.hollowed_at = None
        session.add(user)
        if commit:
            await session.commit()
        if trigger_rescue and user.is_hollowed and not was_hollowed:
            await self.trigger_rescue_protocol(session, user)
        logger.info("HP change user=%s delta=%s source=%s hp=%s", user.id, delta, source, user.hp)
        return user

    async def calculate_daily_drain(self, session: AsyncSession, user: User) -> int:
        if not user.last_active_date:
            return 0
        today = datetime.date.today()
        delta_days = (today - user.last_active_date.date()).days - 1
        if delta_days <= 0:
            return 0

        drain = 10 * delta_days
        await self.apply_hp_change(session, user, -drain, source="daily_inactivity")
        if user.is_hollowed:
            await self.trigger_rescue_protocol(session, user)
        return drain

    async def restore_by_difficulty(self, session: AsyncSession, user: User, difficulty: str | None) -> int:
        diff_key = (difficulty or "E").upper()
        delta = self.HP_RECOVERY_BY_DIFF.get(diff_key, 6)
        await self.apply_hp_change(session, user, delta, source="quest_complete")
        return delta

    async def restore_hp_from_quest(self, session: AsyncSession, user: User, difficulty: str | None) -> User:
        await self.restore_by_difficulty(session, user, difficulty)
        return user

    async def trigger_rescue_protocol(self, session: AsyncSession, user: User) -> str:
        if not user.is_hollowed:
            return ""

        await session.execute(
            update(Quest)
            .where(Quest.user_id == user.id, Quest.status == QuestStatus.ACTIVE.value)
            .values(status=QuestStatus.PAUSED.value)
        )
        await session.commit()

        from app.services.dungeon_service import dungeon_service
        rescue = await dungeon_service.start_dungeon(session, user.id, dungeon_type="RESCUE", duration_minutes=30)
        return rescue.get("message", "⚠️ Hollowed Protocol 啟動。")

    async def get_hp_display(self, user: User) -> dict:
        hp = int(user.hp or 0)
        max_hp = int(user.max_hp or 100)
        percentage = int((hp / max_hp) * 100) if max_hp else 0
        status = user.hp_status or self.STATUS_HEALTHY
        emoji_map = {
            self.STATUS_HEALTHY: "💚",
            self.STATUS_CRITICAL: "🧡",
            self.STATUS_HOLLOWED: "🖤",
            self.STATUS_RECOVERING: "💛",
        }
        return {
            "hp": hp,
            "max_hp": max_hp,
            "percentage": percentage,
            "status": status,
            "emoji": emoji_map.get(status, "💚"),
        }


hp_service = HPService()
