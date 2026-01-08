from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import os
from sqlalchemy import select
from sqlalchemy.sql import func
import datetime
import random
import uuid
from legacy.models.quest import Quest, Goal, GoalStatus, QuestStatus, QuestType
from legacy.services.ai_engine import ai_engine
import logging

logger = logging.getLogger(__name__)


class QuestService:
    DAILY_QUEST_COUNT = 3
    DAILY_HABIT_COUNT = 2
    DEFAULT_DAILY_HABITS = [
        {"tag": "補水", "name": "補水"},
        {"tag": "伸展", "name": "伸展"},
        {"tag": "整理桌面", "name": "整理桌面"},
    ]

    async def get_daily_quests(self, session: AsyncSession, user_id: str):
        """
        Fetches active quests for today.
        If none exist, generates a fresh batch (Daily Reset).
        """
        today = datetime.date.today()

        # 1. Fetch Existing Quests for Today (or Active ones)
        # We look for quests scheduled for today OR active pending ones?
        # For simplicity: "Daily Quests" are those created today date or scheduled for today.
        stmt = (
            select(Quest)
            .where(Quest.user_id == user_id, func.date(Quest.created_at) == today)
            .order_by(Quest.created_at.asc())
        )
        result = await session.execute(stmt)
        quests = result.scalars().all()

        # 2. If no quests, Generate Daily Batch
        if not quests:
            quests = await self._generate_daily_batch(session, user_id)

        return quests[: self.DAILY_QUEST_COUNT]

    async def create_new_goal(
        self, session: AsyncSession, user_id: str, goal_text: str
    ):
        """
        Creates a new Goal and uses AI to break it down into Milestones (Main Quests).
        """
        # 1. Create Goal Record
        goal = Goal(user_id=user_id, title=goal_text, status=GoalStatus.ACTIVE.value)
        session.add(goal)
        await session.flush()  # Get ID

        # 2. AI Decomposition
        system_prompt = (
            "你是戰術拆解代理人。請將長期目標拆解為『今天就能完成』的任務。"
            "語言：輸出內容必須是繁體中文。"
            "請輸出 JSON ONLY，並符合格式："
            "{"
            '"tactical_quests": ['
            '{"title": "str", "desc": "str", "difficulty": "E|D|C", '
            '"duration_minutes": 10, "definition_of_done": "str"}'
            "],"
            '"daily_habits": ['
            '{"title": "str", "desc": "str"}'
            "]"
            "}"
            "規則："
            "1) tactical_quests 必須剛好 3 個，每個 <= 60 分鐘。"
            "2) daily_habits 必須剛好 2 個。"
            "3) 任務需包含明確完成條件（definition_of_done）。"
        )
        user_prompt = f"Goal: {goal_text}"

        try:
            ai_plan = await ai_engine.generate_json(system_prompt, user_prompt)
            goal.decomposition_json = ai_plan

            quest_specs = (
                ai_plan.get("tactical_quests")
                or ai_plan.get("milestones")
                or ai_plan.get("micro_missions")
                or ai_plan.get("quests")
                or []
            )
            daily_habits = ai_plan.get("daily_habits", [])[: self.DAILY_HABIT_COUNT]

            def _contains_cjk(text: str) -> bool:
                return any("\u4e00" <= ch <= "\u9fff" for ch in text or "")

            normalized = []
            for m in quest_specs:
                if not isinstance(m, dict):
                    continue
                title = (m.get("title") or "").strip()
                desc = (m.get("desc") or "").strip()
                diff = (m.get("difficulty") or m.get("diff") or "D").upper()
                duration = (
                    m.get("duration_minutes") or m.get("duration") or m.get("minutes")
                )
                done = m.get("definition_of_done") or m.get("done") or ""

                if not title or not _contains_cjk(title):
                    continue
                if duration:
                    desc = f"{desc}（{int(duration)} 分鐘）".strip()
                if done:
                    desc = f"{desc} 完成條件：{done}".strip()
                if desc and not _contains_cjk(desc):
                    desc = "完成一個短任務（10-20 分鐘）。"

                normalized.append(
                    {
                        "title": title,
                        "desc": desc,
                        "difficulty": diff,
                    }
                )

            fallback_quests = [
                {
                    "title": "建立今天的學習清單",
                    "desc": "列出 3 個今日要完成的小步驟（10 分鐘）",
                    "difficulty": "E",
                },
                {
                    "title": "完成一個最小練習題",
                    "desc": "選 1 題簡單題並完成（20 分鐘）",
                    "difficulty": "D",
                },
                {
                    "title": "寫下回顧與下一步",
                    "desc": "記錄 3 行心得與明日計畫（10 分鐘）",
                    "difficulty": "E",
                },
            ]

            milestones = normalized[:3]
            if len(milestones) < 3:
                for t in fallback_quests:
                    if len(milestones) >= 3:
                        break
                    milestones.append(t)

            if len(daily_habits) < self.DAILY_HABIT_COUNT:
                defaults = [
                    {"title": "補水", "desc": "喝一杯水"},
                    {"title": "伸展", "desc": "做 3 分鐘伸展"},
                ]
                for h in defaults:
                    if len(daily_habits) >= self.DAILY_HABIT_COUNT:
                        break
                    daily_habits.append(h)

            # 3. Create Milestones (Main Quests)
            for m in milestones:
                q = Quest(
                    user_id=user_id,
                    goal_id=goal.id,
                    title=m.get("title", "未命名里程碑"),
                    description=m.get("desc", ""),
                    difficulty_tier=m.get("difficulty", "C"),
                    quest_type=QuestType.MAIN.value,
                    status=QuestStatus.PENDING.value,
                    xp_reward=100,
                )
                session.add(q)

            # 4. Create Habits (Persistent Trackers)
            from legacy.models.dda import HabitState

            for h in daily_habits:
                habit_tag = h.get("title", "新習慣")
                habit = HabitState(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    habit_tag=habit_tag,
                    habit_name=habit_tag,
                    tier="T1",
                    ema_p=0.6,
                    last_zone="YELLOW",
                    zone_streak_days=0,
                    current_tier=1,
                    exp=0,
                )
                session.add(habit)

            await session.commit()
            return goal, ai_plan

        except Exception as e:
            logger.error(f"Goal Decomposition Failed: {e}")
            # Fallback
            await session.commit()
            return goal, {}

    async def trigger_push_quests(
        self, session: AsyncSession, user_id: str, time_block: str = "Morning"
    ):
        """
        DDA Push Logic: Triggers quest generation based on time of day.
        time_block: 'Morning' | 'Midday' | 'Night'
        """
        # 1. Check if we already have quests generated for this block?
        # Actually _generate_daily_batch logic creates a batch.
        # If we want granular pushes, we should check if ACTIVE quests exist.
        stmt = select(Quest).where(
            Quest.user_id == user_id,
            Quest.status == QuestStatus.ACTIVE.value,
            func.date(Quest.created_at) == datetime.date.today(),
        )
        existing = (await session.execute(stmt)).scalars().all()

        # If user has > 2 active quests, don't push more (avoid flooding)
        if len(existing) >= 3:
            return []

        # Generate contextually
        return await self._generate_daily_batch(
            session, user_id, time_context=time_block
        )

    async def _generate_daily_batch(
        self, session: AsyncSession, user_id: str, time_context: str = "Daily"
    ):
        """Generates quests. Checks for BOSS MODE first."""
        from legacy.services.rival_service import rival_service
        from legacy.services.user_service import user_service

        # 0. Boss Mode Check (Only if Morning/Daily context)
        if time_context in ["Daily", "Morning"]:
            user = await user_service.get_user(session, user_id)
            rival = await rival_service.get_rival(session, user_id)

            # Hollowed State: force emergency recovery quest
            is_hollowed = getattr(user, "is_hollowed", False) is True
            hp_status = getattr(user, "hp_status", "")
            hp_value = getattr(user, "hp", None)
            has_hp_value = isinstance(hp_value, (int, float))

            if user and (
                is_hollowed
                or hp_status == "HOLLOWED"
                or (has_hp_value and hp_value <= 0)
            ):
                emergency = Quest(
                    user_id=user_id,
                    title="緊急修復任務",
                    description="完成此任務以重啟系統（回復 10 HP）。",
                    difficulty_tier="F",
                    xp_reward=0,
                    quest_type=QuestType.REDEMPTION.value,
                    status=QuestStatus.ACTIVE.value,
                    scheduled_date=datetime.date.today(),
                    is_redemption=True,
                )
                session.add(emergency)
                await session.commit()
                return [emergency]

            if user and rival and rival.level >= (user.level + 2):
                logger.warning(
                    f"BOSS MODE TRIGGERED for {user_id}. Rival Lv.{rival.level} vs User Lv.{user.level}"
                )

                system_prompt = (
                    "You are an enemy AI 'Viper'. The user is weak. "
                    "Generate 1 HARD 'Boss Quest' to humiliate them. "
                    "Language: ALWAYS use Traditional Chinese (繁體中文). "
                    "Output JSON: { 'title': 'Defeat Viper: [Task]', 'desc': 'Doing this might save your data.', 'diff': 'S', 'xp': 500 }"
                )
                user_prompt = "Generate Boss Quest."

                try:
                    ai_data = await asyncio.wait_for(
                        ai_engine.generate_json(system_prompt, user_prompt), timeout=4.0
                    )
                    t = ai_data if isinstance(ai_data, dict) else ai_data[0]
                    boss_quest = Quest(
                        user_id=user_id,
                        title=t.get("title", "Defeat Viper: System Purge"),
                        description=t.get(
                            "desc", "Complete this to reboot your LifeOS."
                        ),
                        difficulty_tier=t.get("diff", "S"),
                        xp_reward=t.get("xp", 500),
                        quest_type=QuestType.MAIN.value,
                        status=QuestStatus.ACTIVE.value,
                        scheduled_date=datetime.date.today(),
                        is_redemption=True,
                    )
                    session.add(boss_quest)
                    await session.commit()
                    return [boss_quest]
                except Exception as e:
                    logger.error(f"Boss AI Failed: {e}")
                    bq = Quest(
                        user_id=user_id,
                        title="Defeat Viper: Manual Override",
                        description="Do 50 Pushups or Clean your entire room.",
                        difficulty_tier="S",
                        xp_reward=500,
                        quest_type=QuestType.MAIN.value,
                        status=QuestStatus.ACTIVE.value,
                        scheduled_date=datetime.date.today(),
                        is_redemption=True,
                    )
                    session.add(bq)
                    await session.commit()
                    return [bq]

        # 1. Normal Flow - Active Goal & DDA
        stmt = select(Goal).where(
            Goal.user_id == user_id, Goal.status == GoalStatus.ACTIVE.value
        )
        result = await session.execute(stmt)
        active_goal = result.scalars().first()

        topic = (
            f"Current Objective: {active_goal.title}"
            if active_goal
            else "General Cyberpunk Self-Improvement"
        )

        # DDA Check (Feature 3)
        from legacy.models.dda import DailyOutcome

        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        dda_stmt = select(DailyOutcome).where(
            DailyOutcome.user_id == user_id,
            func.date(DailyOutcome.date) == yesterday,
            DailyOutcome.is_global.is_(True),
        )
        dda_res = (await session.execute(dda_stmt)).scalars().first()

        dda_modifier = ""
        target_diff = "D"
        if dda_res and not dda_res.done:
            dda_modifier = (
                "User is struggling. Generate EASIER, shorter tasks. Focus on recovery."
            )
            target_diff = "E"
            logger.info(f"DDA Triggered: Easy Mode for {user_id}")

        # Serendipity Check (Feature 3)
        force_serendipity = os.environ.get("FORCE_SERENDIPITY") == "1"
        disable_serendipity = os.environ.get("DISABLE_SERENDIPITY") == "1"
        is_lucky = False
        if force_serendipity:
            is_lucky = True
        elif (
            not disable_serendipity
            and os.environ.get("TESTING") != "1"
            and not os.environ.get("PYTEST_CURRENT_TEST")
        ):
            is_lucky = random.random() < 0.2  # 20%
        serendipity_prompt = ""
        if is_lucky:
            serendipity_prompt = (
                "其中 1 個任務標記為「稀有」，標題加上「稀有」並提高 XP 至 50。"
            )

        # 2. Generate with AI
        count = self.DAILY_QUEST_COUNT if time_context in ["Daily", "Morning"] else 1
        system_prompt = (
            f"Generate EXACTLY {count} Daily Tactical Side-Quests. {dda_modifier} "
            f"Time Context: {time_context} (Customize tasks for this time). "
            f"Theme: Cyberpunk/Gamified Life. "
            f"Language: ALWAYS use Traditional Chinese (繁體中文). "
            f"Output JSON list ONLY: [ {{ 'title': 'str', 'desc': 'str', 'diff': '{target_diff}', 'xp': 20 }} ] "
            f"{serendipity_prompt}"
        )
        user_prompt = f"Context: {topic}. Generate tasks."

        new_quests = []

        try:
            # Enforce 3s timeout for responsiveness
            ai_data = await asyncio.wait_for(
                ai_engine.generate_json(system_prompt, user_prompt),
                timeout=3.0,
            )

            if isinstance(ai_data, dict) and ai_data.get("error"):
                # Fallback logic...
                raise ValueError("AI Error")

            quest_list = (
                ai_data if isinstance(ai_data, list) else ai_data.get("quests", [])
            )
            if isinstance(ai_data, dict) and not quest_list:
                # Try to parse single object or flat dict
                if "title" in ai_data:
                    quest_list = [ai_data]

            def _contains_cjk(text: str) -> bool:
                return any("\u4e00" <= ch <= "\u9fff" for ch in text)

            normalized = []
            for t in quest_list:
                if not isinstance(t, dict):
                    continue
                title = (t.get("title") or "").strip()
                desc = (t.get("desc") or "").strip()
                diff = t.get("diff", target_diff)
                xp = t.get("xp", 20)

                if not title or not _contains_cjk(title):
                    continue
                if desc and not _contains_cjk(desc):
                    desc = "完成一個短任務（10-20 分鐘）。"

                normalized.append(
                    {"title": title, "desc": desc, "diff": diff, "xp": xp}
                )

            quest_list = normalized[:count]

            fallback_templates = [
                {
                    "title": "系統重啟",
                    "desc": "5 分鐘深呼吸或走動（備援）",
                    "diff": "E",
                    "xp": 10,
                },
                {
                    "title": "資料同步",
                    "desc": "記錄 3 句今日進度（備援）",
                    "diff": "D",
                    "xp": 20,
                },
                {
                    "title": "硬體維護",
                    "desc": "整理桌面 10 分鐘（備援）",
                    "diff": "D",
                    "xp": 20,
                },
            ]

            if is_lucky and quest_list:
                quest_list[0]["title"] = f"稀有｜{quest_list[0]['title']}"
                quest_list[0]["xp"] = max(quest_list[0].get("xp", 20), 50)
                quest_list[0]["diff"] = quest_list[0].get("diff", "C")

            if len(quest_list) < count:
                for t in fallback_templates:
                    if len(quest_list) >= count:
                        break
                    quest_list.append(t)

            for t in quest_list[:count]:
                q = Quest(
                    user_id=user_id,
                    title=t.get("title", "Daily Task"),
                    description=t.get("desc", ""),
                    difficulty_tier=t.get("diff", target_diff),
                    xp_reward=t.get("xp", 20),
                    quest_type=QuestType.SIDE.value,
                    status=QuestStatus.ACTIVE.value,
                    scheduled_date=datetime.date.today(),
                )
                session.add(q)
                new_quests.append(q)

        except (Exception, asyncio.TimeoutError) as e:
            if isinstance(e, asyncio.TimeoutError):
                logger.warning("AI Quest Gen Timeout - Using Fallback")
            else:
                logger.error(f"AI Quest Gen Failed: {e}")

            # Fallback to Templates
            templates = [
                {
                    "title": "系統重啟",
                    "desc": "5 分鐘深呼吸或走動（備援）",
                    "diff": "E",
                    "xp": 10,
                },
                {
                    "title": "資料同步",
                    "desc": "記錄 3 句今日進度（備援）",
                    "diff": "D",
                    "xp": 20,
                },
                {
                    "title": "硬體維護",
                    "desc": "整理桌面 10 分鐘（備援）",
                    "diff": "D",
                    "xp": 20,
                },
            ]
            for t in templates[:count]:
                q = Quest(
                    user_id=user_id,
                    title=t["title"],
                    description=t["desc"],
                    difficulty_tier=t["diff"],
                    xp_reward=t["xp"],
                    quest_type=QuestType.SIDE.value,
                    status=QuestStatus.ACTIVE.value,
                    scheduled_date=datetime.date.today(),
                )
                session.add(q)
                new_quests.append(q)

        await session.commit()
        return new_quests

    async def complete_quest(
        self, session: AsyncSession, user_id: str, quest_id: str
    ) -> dict:
        """
        Marks a quest as DONE and returns Reward Data (RPE integrated).
        Returns Dict with quest and reward details.
        """
        stmt = select(Quest).where(Quest.id == quest_id, Quest.user_id == user_id)
        result = await session.execute(stmt)
        quest = result.scalars().first()

        if quest and quest.status != QuestStatus.DONE.value:
            quest.status = QuestStatus.DONE.value
            
            # --- Loot & RPE Logic ---
            from application.services.loot_service import loot_service
            
            # Calculate Reward
            loot = loot_service.calculate_reward(quest.difficulty_tier, "C") # Default tier C for now
            
            # Apply XP to user (simplistic for now, ideally needs UserService.add_xp)
            # We will just return the loot data, caller (GameLoop) or a dedicated handler should apply it?
            # Or we apply it here if we access user.
            from legacy.services.user_service import user_service
            user = await user_service.get_user(session, user_id)
            if user:
                user.exp = (user.exp or 0) + loot.xp
                # Gold? We don't have Gold column in User model yet?
                # Assuming simple XP for now.
            
            await session.commit()
            
            # Passive Boss Damage
            from legacy.services.boss_service import boss_service
            await boss_service.deal_damage(session, user_id, 50)  # 50 dmg per quest
            
            # Hollowed recovery
            if user and quest.quest_type == QuestType.REDEMPTION.value:
                from legacy.services.hp_service import hp_service
                if user.is_hollowed or getattr(user, "hp_status", "") == "HOLLOWED":
                    target_hp = min(user.max_hp or 100, 10)
                    delta = target_hp - (user.hp or 0)
                    if delta:
                        await hp_service.apply_hp_change(
                            session, user, delta, source="rescue_quest", trigger_rescue=False
                        )
            elif user:
                from legacy.services.hp_service import hp_service
                await hp_service.restore_by_difficulty(session, user, quest.difficulty_tier)
                
            return {
                "quest": quest,
                "loot": loot
            }
        return None

    async def reroll_quests(self, session: AsyncSession, user_id: str):
        """Archives current daily quests and generates new ones. Returns (new_quests, viper_taunt)."""
        today = datetime.date.today()

        # Archive old ones
        stmt = select(Quest).where(
            Quest.user_id == user_id,
            func.date(Quest.created_at) == today,
            Quest.status != QuestStatus.DONE.value,
        )
        result = await session.execute(stmt)
        failed_quests = result.scalars().all()

        viper_taunt = None
        if failed_quests:
            # Proactive Nuance: Viper mocks failure
            # We need to fetch User/Rival
            from legacy.services.rival_service import rival_service
            from legacy.services.user_service import user_service

            user = await user_service.get_user(session, user_id)
            rival = await rival_service.get_rival(session, user_id)

            if user and rival:
                # Construct context
                count = len(failed_quests)
                context_prompt = (
                    f"User failed {count} quests (e.g. '{failed_quests[0].title}')."
                )

                # Feature 4: Viper Taunt via NarrativeService
                from legacy.services.narrative_service import narrative_service

                viper_taunt = await narrative_service.get_viper_comment(
                    session, user_id, context_prompt
                )

        for q in failed_quests:
            await session.delete(q)  # Reset logic

        await session.commit()

        new_quests = await self._generate_daily_batch(session, user_id)
        return new_quests, viper_taunt

    async def get_active_habits(self, session: AsyncSession, user_id: str):
        from legacy.models.dda import HabitState

        stmt = select(HabitState).where(HabitState.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def _seed_default_habits(
        self, session: AsyncSession, user_id: str, habits: list
    ):
        from legacy.models.dda import HabitState

        existing = {
            (h.habit_tag or h.habit_name or "").strip()
            for h in habits
            if (h.habit_tag or h.habit_name)
        }

        created = False
        for template in self.DEFAULT_DAILY_HABITS:
            if len(habits) >= self.DAILY_HABIT_COUNT:
                break
            tag = template["tag"]
            if tag in existing:
                continue
            habit = HabitState(
                user_id=user_id,
                habit_tag=tag,
                habit_name=template["name"],
                tier="T1",
                ema_p=0.6,
                last_zone="YELLOW",
                zone_streak_days=0,
                current_tier=1,
                exp=0,
            )
            session.add(habit)
            habits.append(habit)
            existing.add(tag)
            created = True

        if created:
            await session.commit()
        return habits

    async def get_daily_habits(
        self, session: AsyncSession, user_id: str, limit: int | None = None
    ):
        habits = await self.get_active_habits(session, user_id)
        target = limit or self.DAILY_HABIT_COUNT
        if len(habits) < target:
            habits = await self._seed_default_habits(session, user_id, habits)

        def habit_sort(habit):
            last = habit.last_outcome_date or datetime.date.min
            streak = habit.zone_streak_days or 0
            return (last, streak)

        habits = sorted(habits, key=habit_sort)
        return habits[:target]


quest_service = QuestService()
