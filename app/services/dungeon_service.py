import datetime
import uuid
import logging
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dungeon import (
    Dungeon,
    DungeonStage,
    DungeonStatus,
    DungeonType,
    DUNGEON_TEMPLATES,
)
from app.models.user import User
from app.services.loot_service import loot_service
from app.models.gamification import ItemRarity

logger = logging.getLogger(__name__)


class DungeonService:
    async def get_active_dungeon(self, session: AsyncSession, user_id: str):
        stmt = select(Dungeon).where(
            Dungeon.user_id == user_id,
            Dungeon.status == DungeonStatus.ACTIVE.value,
        )
        result = await session.execute(stmt)
        scalars = result.scalars()
        if asyncio.iscoroutine(scalars):
            scalars = await scalars
        dungeon = scalars.first()
        if asyncio.iscoroutine(dungeon):
            dungeon = await dungeon
        if (
            dungeon
            and dungeon.deadline
            and (
                dungeon.deadline.replace(tzinfo=datetime.timezone.utc)
                if dungeon.deadline.tzinfo is None
                else dungeon.deadline
            )
            < datetime.datetime.now(
                (dungeon.deadline.tzinfo or datetime.timezone.utc)
            )
        ):
            dungeon.status = DungeonStatus.FAILED.value
            await session.commit()
            return None
        return dungeon

    async def open_dungeon(
        self, session: AsyncSession, user_id: str, dungeon_type: str
    ) -> tuple[Dungeon | None, str]:
        active = await self.get_active_dungeon(session, user_id)
        if active:
            return None, "已經在副本中，無法重複開啟。"

        dtype = (dungeon_type or "").upper()
        template = DUNGEON_TEMPLATES.get(
            dtype, DUNGEON_TEMPLATES[DungeonType.FOCUS.value]
        )

        dungeon_id = str(uuid.uuid4())
        deadline = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            minutes=template["duration_minutes"]
        )
        dungeon = Dungeon(
            id=dungeon_id,
            user_id=user_id,
            dungeon_type=dtype,
            name=template["name"],
            duration_minutes=template["duration_minutes"],
            status=DungeonStatus.ACTIVE.value,
            deadline=deadline,
            xp_reward=template.get("xp_reward", 100),
        )
        session.add(dungeon)

        for idx, stage in enumerate(template["stages"], start=1):
            session.add(
                DungeonStage(
                    id=str(uuid.uuid4()),
                    dungeon_id=dungeon_id,
                    title=stage["title"],
                    description=stage.get("desc", ""),
                    order=idx,
                )
            )

        await session.commit()
        return (
            dungeon,
            f"🚪 副本已開啟：{dungeon.name}（{dungeon.duration_minutes} 分鐘）",
        )

    async def get_dungeon_stages(self, session: AsyncSession, dungeon_id: str):
        stmt = (
            select(DungeonStage)
            .where(DungeonStage.dungeon_id == dungeon_id)
            .order_by(DungeonStage.order)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def complete_stage(
        self, session: AsyncSession, user_id: str
    ) -> tuple[bool, str]:
        dungeon = await self.get_active_dungeon(session, user_id)
        if not dungeon:
            return False, "沒有進行中的副本。"

        stages = await self.get_dungeon_stages(session, dungeon.id)
        pending = [s for s in stages if not s.is_complete]
        if not pending:
            return False, "所有階段已完成。"

        target = pending[0]
        target.is_complete = True
        target.completed_at = datetime.datetime.now(datetime.timezone.utc)
        await session.commit()

        completed_count = len([s for s in stages if s.is_complete])
        if completed_count == len(stages):
            dungeon.status = DungeonStatus.COMPLETED.value
            dungeon.completed_at = datetime.datetime.now(datetime.timezone.utc)
            session.add(dungeon)
            await session.commit()

            if dungeon.dungeon_type == DungeonType.RESCUE.value:
                user = await session.get(User, user_id)
                if user:
                    from app.services.hp_service import hp_service

                    target_hp = min(user.max_hp or 100, 30)
                    delta = target_hp - (user.hp or 0)
                    if delta:
                        await hp_service.apply_hp_change(
                            session,
                            user,
                            delta,
                            source="rescue_dungeon",
                            trigger_rescue=False,
                        )

            loot_item = await loot_service.grant_guaranteed_drop(
                session, user_id, min_rarity=ItemRarity.RARE
            )
            loot_text = f"戰利品：{loot_item.name}" if loot_item else "戰利品：無"
            return True, f"🏆 副本通關！{loot_text}"

        return (
            True,
            f"✅ 階段完成：{target.title}（進度：{completed_count}/{len(stages)}）",
        )

    async def abandon_dungeon(
        self, session: AsyncSession, user_id: str
    ) -> tuple[bool, str]:
        dungeon = await self.get_active_dungeon(session, user_id)
        if not dungeon:
            return False, "沒有進行中的副本。"
        dungeon.status = DungeonStatus.ABANDONED.value
        await session.commit()
        return True, "已放棄副本。"

    async def get_remaining_time(self, dungeon: Dungeon) -> str:
        if not dungeon.deadline:
            return "00:00"
        deadline = (
            dungeon.deadline.replace(tzinfo=datetime.timezone.utc)
            if dungeon.deadline.tzinfo is None
            else dungeon.deadline
        )
        remaining = deadline - datetime.datetime.now(deadline.tzinfo)
        seconds = max(int(remaining.total_seconds()), 0)
        minutes, secs = divmod(seconds, 60)
        return f"{minutes:02d}:{secs:02d}"

    async def start_dungeon(
        self,
        session: AsyncSession,
        user_id: str,
        dungeon_type: str = "FOCUS",
        duration_minutes: int = 60,
    ):
        dtype = (dungeon_type or "FOCUS").upper()
        template = DUNGEON_TEMPLATES.get(
            dtype, DUNGEON_TEMPLATES[DungeonType.FOCUS.value]
        )
        template = {**template, "duration_minutes": duration_minutes}
        DUNGEON_TEMPLATES[dtype] = template
        dungeon, msg = await self.open_dungeon(session, user_id, dtype)
        return {"success": dungeon is not None, "message": msg}


dungeon_service = DungeonService()
