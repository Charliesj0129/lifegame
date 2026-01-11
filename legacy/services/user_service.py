from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from legacy.models.action_log import ActionLog
from legacy.services.accountant import accountant
from legacy.services.ai_engine import ai_engine
from legacy.services.loot_service import loot_service
from legacy.services.inventory_service import inventory_service
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

from app.schemas.game_schemas import ProcessResult


class UserService:
    async def get_or_create_user(self, session: AsyncSession, line_user_id: str, name: str = "Unknown") -> User:
        result = await session.execute(select(User).where(User.id == line_user_id))
        user = result.scalars().first()
        if not user:
            user = User(id=line_user_id, name=name)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        if user.push_times is None:
            user.push_times = {"morning": "08:00", "midday": "12:30", "night": "21:00"}
            session.add(user)
            await session.commit()
        return user

    async def get_user(self, session: AsyncSession, line_user_id: str) -> User | None:
        result = await session.execute(select(User).where(User.id == line_user_id))
        return result.scalars().first()

    async def apply_penalty(self, session: AsyncSession, user: User, penalty_type: str = "SOFT_DEATH"):
        """
        The Abyss System: Enforces Loss Aversion.
        """
        if penalty_type == "SOFT_DEATH":
            # Taking the concept of "Permadeath" but keeping items.
            # Reset Level and Attributes, but keep Items/Lore.
            user.level = 1
            user.xp = 0
            # user.str = 1 # Optional: Hardcore mode would reset stats too.
            # user.int = 1
            # user.vit = 1
            # user.wis = 1
            # user.cha = 1
            # For "Soft" death, just major XP/Level loss is enough pain.
            session.add(user)
            await session.commit()
            logger.warning(f"User {user.id} suffered SOFT_DEATH penalty.")

    async def check_hollowing(self, session: AsyncSession, user: User) -> bool:
        """
        Checks if user has triggered the 'Hollowing' state (Inactivity).
        """
        from datetime import datetime, timedelta, timezone

        if not user.last_active_date:
            return False

        now = datetime.now(timezone.utc)
        # Threshold: 48 hours (Configurable)
        threshold = timedelta(hours=48)

        if (now - user.last_active_date) > threshold and not user.is_hollowed:
            user.is_hollowed = True
            user.hp_status = "HOLLOWED"
            session.add(user)
            await session.commit()
            return True
        return False

    async def process_action(self, session: AsyncSession, line_user_id: str, text: str) -> ProcessResult:
        # 1. Get User

        user = await self.get_or_create_user(session, line_user_id)

        # 2. Fast/Slow Router (System 1 vs System 2)

        # Fast Mode Criteria
        is_fast_mode = False
        ai_result = {}

        normalized_text = text.lower().strip()
        if len(text) < 15:
            if any(k in normalized_text for k in ["gym", "run", "lift", "workout", "str"]):
                ai_result = {
                    "stat_type": "STR",
                    "difficulty_tier": "C",
                    "narrative": "⚡ [System 1] 肌肉纖維損傷偵測。生長機制啟動。",
                    "loot_drop": {"has_loot": False},
                }
                is_fast_mode = True
            elif any(k in normalized_text for k in ["study", "code", "read", "learn", "int"]):
                ai_result = {
                    "stat_type": "INT",
                    "difficulty_tier": "C",
                    "narrative": "⚡ [System 1] 神經通路強化。突觸傳導率提升。",
                    "loot_drop": {"has_loot": False},
                }
                is_fast_mode = True
            elif any(k in normalized_text for k in ["sleep", "eat", "rest", "food", "vit"]):
                ai_result = {
                    "stat_type": "VIT",
                    "difficulty_tier": "D",
                    "narrative": "⚡ [System 1] 生物系統修復中。體內平衡恢復。",
                    "loot_drop": {"has_loot": False},
                }
                is_fast_mode = True

        # Default values
        attribute = "VIT"
        difficulty = "E"
        narrative = "Processing..."
        xp_gain = 0
        has_loot = False  # TODO: brain triggers loot

        if is_fast_mode:
            attribute = ai_result.get("stat_type", "VIT")
            difficulty = ai_result.get("difficulty_tier", "E")
            narrative = ai_result.get("narrative", "數據已上傳。")

            # Accountant Math for System 1
            raw_xp = accountant.calculate_xp(attribute, difficulty)
        else:
            # Phase 4: Brain Service (System 2)
            from application.services.brain_service import brain_service

            plan = await brain_service.think_with_session(session, user.id, text)

            narrative = plan.narrative
            difficulty = plan.flow_state.get("tier", "C")

            if plan.stat_update:
                attribute = plan.stat_update.stat_type
                raw_xp = plan.stat_update.xp_amount
                # Apply HP/Gold changes from Brain
                if plan.stat_update.hp_change != 0:
                    user.hp = max(0, min(100, user.hp + plan.stat_update.hp_change))
                if plan.stat_update.gold_change != 0:
                    user.gold += plan.stat_update.gold_change
            else:
                raw_xp = 10  # Fallback

        # Apply Buffs (Common Logic)
        active_buffs = await inventory_service.get_active_buffs(session, user.id)
        xp_gain = accountant.apply_buffs(raw_xp, active_buffs, attribute)

        old_level = user.level
        accountant.apply_xp(user, attribute, xp_gain)

        # 4. Persistence
        log = ActionLog(
            user_id=user.id,
            action_text=text,
            attribute_tag=attribute,
            difficulty_tier=difficulty,
            xp_gained=xp_gain,
        )
        session.add(log)

        # DDA: Habit Tracking (Point 2)
        from legacy.models.dda import HabitState
        from sqlalchemy import select

        # Fetch active habits
        stmt_habits = select(HabitState).where(HabitState.user_id == user.id)
        active_habits = (await session.execute(stmt_habits)).scalars().all()

        habit_update_msg = ""
        matched_habit = None
        for h in active_habits:
            # Simple keyword match
            tag = (h.habit_tag or "").lower()
            if tag and tag in normalized_text:
                matched_habit = h
                break

        if matched_habit:
            # EMA Update: P_new = P_old * (1-alpha) + 1.0 * alpha
            alpha = 0.2
            matched_habit.ema_p = (matched_habit.ema_p or 0.5) * (1 - alpha) + alpha

            # Tier Logic
            current_ema = matched_habit.ema_p
            old_tier = matched_habit.tier
            new_tier = old_tier

            if current_ema >= 0.8:
                new_tier = "T3"  # Gold
            elif current_ema >= 0.5:
                new_tier = "T2"  # Silver
            else:
                new_tier = "T1"  # Bronze

            matched_habit.tier = new_tier
            habit_update_msg = f"\n📈 習慣[{matched_habit.habit_tag}] 追蹤確認 (EMA: {current_ema:.2f})"
            if new_tier != old_tier:
                habit_update_msg += f" | 升階: {new_tier}!"

            session.add(matched_habit)

        # M6: Update Streak
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)

        streak_broken = False
        if not user.last_active_date:
            user.streak_count = 1
        else:
            if user.streak_count is None:
                user.streak_count = 0
            last_date = user.last_active_date.date()
            today_date = now.date()

            if last_date == today_date:
                pass  # Already active today
            elif last_date == (today_date - timedelta(days=1)):
                user.streak_count += 1  # Consecutive day
            else:
                user.streak_count = 1  # Broken streak
                streak_broken = True

        # Apply HP penalties/recovery
        from legacy.services.hp_service import hp_service

        if streak_broken:
            await hp_service.apply_hp_change(session, user, -20, source="streak_broken", commit=False)

        if attribute == "VIT":
            await hp_service.apply_hp_change(session, user, 5, source="vit_recovery", commit=False)

        user.last_active_date = now
        session.add(user)

        # 5. Lore Unlocking (Point 3)
        lore_msg = ""
        if user.level > old_level:
            # Unlock next chapter of MainStory on Level Up
            from legacy.services.lore_service import lore_service

            prog = await lore_service.unlock_next_chapter(session, user.id, "MainStory")
            lore_msg = f"\n📜 解鎖主線劇情：第 {prog.current_chapter} 章"

        await session.commit()
        if user.is_hollowed:
            from legacy.services.hp_service import hp_service

            await hp_service.trigger_rescue_protocol(session, user)

        # 5. Loot Handling (AI decides IF, Code decides WHAT)
        loot_name = None
        loot_rarity = None

        loot_item = await loot_service.calculate_drop(session, difficulty, force_drop=has_loot)
        if loot_item:
            await loot_service.grant_item(session, user.id, loot_item)
            loot_name = loot_item.name
            loot_rarity = loot_item.rarity.value

        attr_map = {
            "STR": "力量",
            "INT": "智力",
            "VIT": "體力",
            "WIS": "智慧",
            "CHA": "魅力",
        }
        attr_label = attr_map.get(attribute, attribute)

        msg = f"{narrative}\n\n[系統] {attr_label} +{xp_gain} 經驗"

        if streak_broken:
            msg += "\n💔 連勝中斷！生命值 -20"
        if user.is_hollowed:
            msg += "\n🩸 你已進入【瀕死狀態】。請完成緊急修復任務。"

        if habit_update_msg:
            msg += habit_update_msg

        if loot_name:
            msg += f"\n🎁 掉落：{loot_name}（{loot_rarity}）"

        if user.level > old_level:
            msg += f"\n🎉 等級提升！目前等級 {user.level}"
            if lore_msg:
                msg += lore_msg

        # Determine Title
        title = "街頭鼠"
        if user.level >= 5:
            title = "跑者"
        if user.level >= 10:
            title = "街頭武士"
        if user.level >= 20:
            title = "賽博傳奇"
        if user.streak_count >= 3:
            title = f"🔥 {title}"

        return ProcessResult(
            text=msg,
            user_id=user.id,
            action_text=text,
            attribute=attribute,
            difficulty_tier=difficulty,
            xp_gained=xp_gain,
            new_level=user.level,
            leveled_up=(user.level > old_level),
            loot_name=loot_name,
            loot_rarity=loot_rarity,
            narrative=narrative,
            current_attributes={
                "STR": user.str,
                "INT": user.int,
                "VIT": user.vit,
                "WIS": user.wis,
                "CHA": user.cha,
            },
            current_xp=user.xp or 0,
            streak_count=user.streak_count,
            user_title=title,
        )


user_service = UserService()
