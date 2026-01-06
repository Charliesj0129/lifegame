from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta, timezone
import random
import logging
from app.models.user import User
from app.models.quest import Rival
from app.models.gamification import UserBuff
from app.services.ai_engine import ai_engine

logger = logging.getLogger(__name__)


class RivalService:
    async def get_or_create_rival(
        self, session: AsyncSession, user_id: str, initial_level: int = 1
    ) -> Rival:
        result = await session.execute(select(Rival).where(Rival.user_id == user_id))
        rival = result.scalars().first()
        if not rival:
            rival = Rival(
                user_id=user_id, name="Viper", level=max(1, initial_level), xp=0
            )
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
        if not user.last_active_date:
            return ""

        delta = now.date() - user.last_active_date.date()
        missed_days = delta.days - 1

        narrative = ""

        if missed_days > 0:
            logger.info(f"Viper: User missed {missed_days} days.")

            # 2. Nemesis Growth
            xp_gain = missed_days * 100
            rival.xp += xp_gain

            # Simple Leveling: Lv = 1 + XP // 1000
            new_level = 1 + (rival.xp // 1000)
            if new_level > rival.level:
                rival.level = new_level
                narrative += f"\n⚠️ **Viper 升級！**（Lv.{rival.level}）"

            # 3. Theft (Resource Siphoning)
            theft_xp = int((user.xp or 0) * 0.05 * missed_days)  # 5% per day
            theft_gold = int((user.gold or 0) * 0.05 * missed_days)

            if theft_xp > 0 or theft_gold > 0:
                user.xp = max(0, (user.xp or 0) - theft_xp)
                user.gold = max(0, (user.gold or 0) - theft_gold)
                narrative += (
                    f"\n💸 入侵警報：Viper 竊取 {theft_xp} 經驗與 {theft_gold} 金幣。"
                )

            # 4. Debuff (Sabotage) - If Rival is stronger or random chance
            # Only apply if Rival Lv > User Lv
            if rival.level > user.level:
                # Apply a random debuff
                target = random.choice(["STR", "VIT", "INT"])
                # Check if already debuffed to avoid spamming
                # For MVP, just add it. UserBuff supports multiple.

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
        session.add(user)  # Persist theft
        await session.commit()

        return narrative

    async def advance_daily_briefing(self, session: AsyncSession, user: User) -> Rival:
        """Daily briefing update for rival progression."""
        rival = await self.get_or_create_rival(
            session, user.id, initial_level=user.level
        )

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
        """Generates a contextual taunt using AI."""
        try:
            # 1. Build Context
            # Simple diff
            str_diff = rival.level - user.level
            status_context = "Rival is stronger." if str_diff > 0 else "MATCHED."

            system_prompt = (
                "You are 'Viper', an arrogant AI rival in a Cyberpunk LifeRPG. "
                "The user is your competitor. "
                "Generate a short, stinging 1-sentence taunt based on the stats."
            )
            user_prompt = f"Context: {status_context}. Viper Lv.{rival.level} vs User Lv.{user.level}."

            # 2. Call AI
            # We use generate_json typically, but here we just want text.
            # If ai_engine only has generate_json, we wrap it or add generate_text.
            # Checking ai_engine usage elsewhere... it seems we use generate_json.
            # Let's use generate_json with a schema or just simple text if supported.
            # Looking at ai_engine.py (implied), likely it has generate_content or similar.
            # Let's assume generate_json returns a dict, we can ask for {"taunt": "str"}

            response = await ai_engine.generate_json(
                system_prompt + " Output JSON: {'taunt': 'str'}", user_prompt
            )

            taunt = response.get("taunt", "我正在進化。")
            return f"Viper：「{taunt}」"

        except Exception as e:
            logger.error(f"Taunt Gen Failed: {e}")
            return "Viper：「在你沉睡時，我已進化。」"


rival_service = RivalService()
