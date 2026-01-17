from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta, timezone
import random
import logging
from app.models.user import User
from app.models.quest import Rival
from app.models.gamification import UserBuff
from application.services.ai_engine import ai_engine

logger = logging.getLogger(__name__)


class RivalService:
    async def get_or_create_rival(self, session: AsyncSession, user_id: str, initial_level: int = 1) -> Rival:
        result = await session.execute(select(Rival).where(Rival.user_id == user_id))
        rival = result.scalars().first()
        if not rival:
            rival = Rival(user_id=user_id, name="Viper", level=max(1, initial_level), xp=0)
            session.add(rival)
            await session.commit()
        return rival

    async def get_rival(self, session: AsyncSession, user_id: str) -> Rival | None:
        result = await session.execute(select(Rival).where(Rival.user_id == user_id))
        return result.scalars().first()

    async def process_encounter(self, session: AsyncSession, user: User) -> str:
        """
        Main entry point called on Webhook.
        Checks User inactivity and triggers Rival growth/sabotage.
        Returns a narrative string (e.g. Taunt or Null).
        """
        rival = await self.get_or_create_rival(session, user.id)

        # 1. Inactivity Check
        now = datetime.now(timezone.utc)
        # Simplify: If last_active was yesterday or today, no penalty.
        # If last_active was < T-1 day, we have missed days.

        # We need to rely on the fact that 'user.last_active_date' hasn't been updated YET for this request
        # But 'process_action' updates it.
        # So we should call this BEFORE updating user.last_active_date.

        # Calculating days missed
        # If last_active is None (new user), no penalty.
        from domain.rules.rival_rules import RivalRules

        if not user.last_active_date:
            return ""

        now_date = now.date()
        last_active_date = user.last_active_date.date()

        result = RivalRules.calculate_inactivity_penalty(
            last_active_date, now_date, user.xp or 0, user.gold or 0, user.level or 1, rival.level or 1, rival.xp or 0
        )

        if result.missed_days <= 0:
            return ""

        logger.info(f"Viper: User missed {result.missed_days} days.")

        # Initialize narrative for building response
        narrative = f"⚠️ Viper 偵測到 {result.missed_days} 日離線。"

        # Apply Logic Result
        rival.xp += result.rival_xp_gain
        if result.rival_level_up:
            # We assume rule handles "level up condition", but here we just have a bool.
            # We recreate the simple level calc or move level calc fully to rule.
            # Rule provides projected state? No, rule provides diffs mostly.
            # Let's trust rule's bool implication or recalculate state if rule is stateless.
            # RivalRules had "projected_level" internally but returned bool.
            # Let's recalculate level based on new XP as simpler implementation.
            rival.level = 1 + (rival.xp // 1000)
            narrative += f"\n⚠️ **Viper 升級！**（Lv.{rival.level}）"

        if result.theft_xp > 0 or result.theft_gold > 0:
            user.xp = max(0, (user.xp or 0) - result.theft_xp)
            user.gold = max(0, (user.gold or 0) - result.theft_gold)
            narrative += f"\n💸 入侵警報：Viper 竊取 {result.theft_xp} 經驗與 {result.theft_gold} 金幣。"

        if result.should_debuff:
            # Apply a random debuff
            target = random.choice(["STR", "VIT", "INT"])
            expires = now + timedelta(hours=24)
            debuff = UserBuff(
                user_id=user.id,
                target_attribute=target,
                multiplier=0.8,  # -20%
                expires_at=expires,
            )
            session.add(debuff)
            narrative += f"\n🦠 病毒植入：{target} 降低 20%（24 小時）。"

        session.add(rival)
        session.add(user)
        await session.commit()

        return narrative

    async def advance_daily_briefing(self, session: AsyncSession, user: User) -> Rival:
        """Daily briefing update for rival progression."""
        rival = await self.get_or_create_rival(session, user.id, initial_level=user.level)

        # Viper Logic: Grows 20-50% of a level per day + some randomness
        growth = random.randint(30, 80)  # XP
        rival.xp += growth
        if rival.xp >= 500:
            rival.level += 1
            rival.xp -= 500

        await session.commit()
        await session.refresh(rival)
        return rival

    async def get_taunt(self, session: AsyncSession, user: User, rival: Rival) -> str:
        """Generates a contextual taunt using AI via NarrativeService."""
        try:
            # 1. Build Context
            context_data = {
                "event": "Random Encounter / Status Check",
                "user_level": user.level or 1,
                "hp_pct": int(((user.hp or 0) / (user.max_hp or 100)) * 100),
                "streak": user.streak_count or 0,
                "gold": user.gold or 0,
            }

            # 2. Delegate to NarrativeService
            from application.services.narrative_service import narrative_service

            return await narrative_service.get_viper_comment(session, user.id, context_data)

        except Exception as e:
            logger.error(f"Taunt Gen Failed: {e}")
            return "Viper：「在你沉睡時，我已進化。」"


rival_service = RivalService()
