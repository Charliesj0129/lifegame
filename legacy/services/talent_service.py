from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from legacy.models.talent import TalentTree, UserTalent, ClassType, EffectType
from app.models.user import User
import uuid
import logging
import random

logger = logging.getLogger(__name__)


class TalentService:
    async def get_talent_tree(self, session: AsyncSession, user_id: str):
        """Fetch talent tree with unlocked state for a user."""
        stmt = select(TalentTree).order_by(TalentTree.tier)
        result = await session.execute(stmt)
        talents = result.scalars().all()

        learned_stmt = (
            select(UserTalent)
            .where(UserTalent.user_id == user_id, UserTalent.is_active.is_(True))
            .options(selectinload(UserTalent.talent))
        )
        learned = (await session.execute(learned_stmt)).scalars().all()
        learned_ids = {t.talent_id for t in learned}

        tree = []
        for talent in talents:
            unlocked = talent.tier == 1 or (
                talent.parent_id and talent.parent_id in learned_ids
            )
            tree.append(
                {
                    "id": talent.id,
                    "tier": talent.tier,
                    "name": talent.name_zh or talent.name,
                    "description": talent.description_zh or talent.description,
                    "class_type": talent.class_type,
                    "unlocked": unlocked,
                    "learned": talent.id in learned_ids,
                }
            )

        return tree

    async def get_user_talents(self, session: AsyncSession, user_id: str):
        """Fetches all talents unlocked by the user."""
        stmt = select(UserTalent).where(
            UserTalent.user_id == user_id, UserTalent.is_active
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def learn_talent(
        self, session: AsyncSession, user_id: str, talent_id: str
    ) -> tuple[bool, str]:
        """Learn a talent by spending points, respecting prerequisites."""
        user_stmt = select(User).where(User.id == user_id)
        user = (await session.execute(user_stmt)).scalars().first()

        talent_stmt = select(TalentTree).where(TalentTree.id == talent_id)
        talent = (await session.execute(talent_stmt)).scalars().first()

        if not user or not talent:
            return False, "找不到使用者或天賦。"

        if (user.talent_points or 0) < (talent.cost or 1):
            return False, "天賦點不足。"

        if talent.parent_id:
            parent_stmt = select(UserTalent).where(
                UserTalent.user_id == user_id,
                UserTalent.talent_id == talent.parent_id,
                UserTalent.is_active.is_(True),
            )
            has_parent = (await session.execute(parent_stmt)).scalars().first()
            if not has_parent:
                return False, "需要前置天賦。"

        existing_stmt = select(UserTalent).where(
            UserTalent.user_id == user_id, UserTalent.talent_id == talent_id
        )
        existing = (await session.execute(existing_stmt)).scalars().first()

        if existing:
            if existing.current_rank >= (talent.max_rank or 1):
                return False, "已達最高等級。"
            existing.current_rank += 1
        else:
            new_talent = UserTalent(
                id=str(uuid.uuid4()),
                user_id=user_id,
                talent_id=talent_id,
                current_rank=1,
            )
            session.add(new_talent)

        user.talent_points = (user.talent_points or 0) - (talent.cost or 1)

        await session.commit()
        name = talent.name_zh or talent.name
        return True, f"已學會【{name}】"

    async def unlock_talent(self, session: AsyncSession, user_id: str, talent_id: str):
        """
        Unlocks or upgrades a talent.
        Checks:
        1. User has enough points.
        2. Prerequisites met (parent unlocked).
        3. Not max rank.
        """
        # 1. Fetch User & Talent
        user_stmt = select(User).where(User.id == user_id)
        user = (await session.execute(user_stmt)).scalars().first()

        talent_stmt = select(TalentTree).where(TalentTree.id == talent_id)
        talent = (await session.execute(talent_stmt)).scalars().first()

        if not user or not talent:
            return {"success": False, "message": "User or Talent not found"}

        # 2. Check Points
        if user.talent_points < talent.cost:
            return {
                "success": False,
                "message": f"Not enough points. Need {talent.cost}, have {user.talent_points}",
            }

        # 3. Check Prerequisites
        if talent.parent_id:
            # Check if user has parent
            parent_check = select(UserTalent).where(
                UserTalent.user_id == user_id, UserTalent.talent_id == talent.parent_id
            )
            has_parent = (await session.execute(parent_check)).scalars().first()
            if not has_parent:
                return {
                    "success": False,
                    "message": "Prerequisite talent not unlocked.",
                }

        # 4. Check Current Rank
        existing_stmt = select(UserTalent).where(
            UserTalent.user_id == user_id, UserTalent.talent_id == talent_id
        )
        existing = (await session.execute(existing_stmt)).scalars().first()

        if existing:
            if existing.current_rank >= talent.max_rank:
                return {"success": False, "message": "Talent already at max rank."}
            existing.current_rank += 1
        else:
            new_talent = UserTalent(
                id=str(uuid.uuid4()),
                user_id=user_id,
                talent_id=talent_id,
                current_rank=1,
            )
            session.add(new_talent)

        # 5. Deduct Points & Apply Effect (Immediate effects if any, usually effects are passive calc)
        user.talent_points -= talent.cost

        await session.commit()
        return {"success": True, "message": f"Unlocked {talent.name}!"}

    async def calculate_bonus(
        self,
        session: AsyncSession,
        user_id: str,
        effect_type: EffectType,
        streak: int | None = None,
    ) -> float:
        """Calculate multiplier based on learned talents."""
        stmt = (
            select(UserTalent)
            .where(UserTalent.user_id == user_id, UserTalent.is_active.is_(True))
            .options(selectinload(UserTalent.talent))
        )
        result = await session.execute(stmt)
        learned = result.scalars().all()

        multiplier = 1.0
        for ut in learned:
            talent = ut.talent
            if not talent:
                continue
            effect = talent.effect_meta or {}
            attr = effect.get("attr")
            val = effect.get("val", 0)
            if effect_type == EffectType.XP_GAIN and attr == "xp_gain":
                if effect.get("type") == "streak" and streak:
                    multiplier += val * streak
                else:
                    multiplier += val

        return multiplier

    async def get_player_class(
        self, session: AsyncSession, user_id: str
    ) -> tuple[ClassType | None, str, str]:
        stmt = (
            select(UserTalent)
            .where(UserTalent.user_id == user_id, UserTalent.is_active.is_(True))
            .options(selectinload(UserTalent.talent))
        )
        learned = (await session.execute(stmt)).scalars().all()
        if not learned:
            return None, "無流派", "⚪"

        counts = {ClassType.WARLORD: 0, ClassType.ALCHEMIST: 0, ClassType.SHADOW: 0}
        for ut in learned:
            if ut.talent and ut.talent.class_type in counts:
                counts[ut.talent.class_type] += 1

        class_type = max(counts, key=counts.get)
        class_info = {
            ClassType.WARLORD: ("狂戰士", "🔴"),
            ClassType.ALCHEMIST: ("煉金術士", "🟡"),
            ClassType.SHADOW: ("影行者", "🟣"),
        }
        class_name, emoji = class_info[class_type]
        return class_type, class_name, emoji

    async def get_player_class_for_ai(self, session: AsyncSession, user_id: str) -> dict:
        class_type, class_name, _emoji = await self.get_player_class(session, user_id)
        if not class_type:
            return {
                "class_type": None,
                "class_name": "無流派",
                "ai_tone": "neutral",
                "keywords": [],
            }

        ai_meta = {
            ClassType.WARLORD: ("aggressive", ["力量", "嗜血"]),
            ClassType.ALCHEMIST: ("analytical", ["煉金", "轉化"]),
            ClassType.SHADOW: ("mysterious", ["閃避", "隱匿"]),
        }
        ai_tone, keywords = ai_meta[class_type]
        return {
            "class_type": class_type,
            "class_name": class_name,
            "ai_tone": ai_tone,
            "keywords": keywords,
        }

    async def check_penalty_evasion(
        self, session: AsyncSession, user_id: str
    ) -> tuple[bool, str]:
        stmt = (
            select(UserTalent)
            .where(UserTalent.user_id == user_id, UserTalent.is_active.is_(True))
            .options(selectinload(UserTalent.talent))
        )
        learned = (await session.execute(stmt)).scalars().all()
        evasion = next(
            (
                ut.talent
                for ut in learned
                if ut.talent and ut.talent.id == "LCK_01_EVASION"
            ),
            None,
        )
        if not evasion:
            return False, ""

        chance = (evasion.effect_meta or {}).get("val", 0.2)
        if random.random() < chance:
            return True, "✨ 閃避成功：懲罰已免除。"
        return False, ""


talent_service = TalentService()
