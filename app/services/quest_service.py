from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from sqlalchemy import select, update
from sqlalchemy.sql import func
import datetime
import random
from app.models.quest import Quest, Goal, GoalStatus, QuestStatus, QuestType
from app.services.ai_engine import ai_engine
import logging
import json

logger = logging.getLogger(__name__)

class QuestService:
    async def get_daily_quests(self, session: AsyncSession, user_id: str):
        """
        Fetches active quests for today. 
        If none exist, generates a fresh batch (Daily Reset).
        """
        today = datetime.date.today()
        
        # 1. Fetch Existing Quests for Today (or Active ones)
        # We look for quests scheduled for today OR active pending ones?
        # For simplicity: "Daily Quests" are those created today date or scheduled for today.
        stmt = select(Quest).where(
            Quest.user_id == user_id,
            func.date(Quest.created_at) == today
        )
        result = await session.execute(stmt)
        quests = result.scalars().all()
        
        # 2. If no quests, Generate Daily Batch
        if not quests:
            quests = await self._generate_daily_batch(session, user_id)
            
        return quests

    async def create_new_goal(self, session: AsyncSession, user_id: str, goal_text: str):
        """
        Creates a new Goal and uses AI to break it down into Milestones (Main Quests).
        """
        # 1. Create Goal Record
        goal = Goal(user_id=user_id, title=goal_text, status=GoalStatus.ACTIVE.value)
        session.add(goal)
        await session.flush() # Get ID

        # 2. AI Decomposition
        system_prompt = (
            "You are a Cyberpunk Tactical Advisor. "
            "Break down the user's High-Level Goal into a tactical plan. "
            "Output JSON ONLY: { "
            "'milestones': [ { 'title': 'str', 'desc': 'str', 'difficulty': 'B' } ], "
            "'daily_habits': [ { 'title': 'str', 'desc': 'str' } ] "
            "}"
        )
        user_prompt = f"Goal: {goal_text}"
        
        try:
            ai_plan = await ai_engine.generate_json(system_prompt, user_prompt)
            goal.decomposition_json = ai_plan
            
            # 3. Create Milestones (Main Quests)
            for m in ai_plan.get("milestones", []):
                q = Quest(
                    user_id=user_id,
                    goal_id=goal.id,
                    title=m.get("title", "Unknown Milestone"),
                    description=m.get("desc", ""),
                    difficulty_tier=m.get("difficulty", "C"),
                    quest_type=QuestType.MAIN.value,
                    status=QuestStatus.PENDING.value,
                    xp_reward=100 # Milestones are big
                )
                session.add(q)
            
            await session.commit()
            return goal, ai_plan
            
        except Exception as e:
            logger.error(f"Goal Decomposition Failed: {e}")
            # Fallback
            await session.commit()
            return goal, {}

    async def _generate_daily_batch(self, session: AsyncSession, user_id: str):
        """Generates quests. Checks for BOSS MODE first."""
        from app.services.rival_service import rival_service
        from app.services.user_service import user_service
        
        # 0. Boss Mode Check
        user = await user_service.get_user(session, user_id)
        rival = await rival_service.get_rival(session, user_id)
        
        if user and rival and rival.level >= (user.level + 2):
            logger.warning(f"BOSS MODE TRIGGERED for {user_id}. Rival Lv.{rival.level} vs User Lv.{user.level}")
            
            # Check if Boss Quest already exists logic is slightly redundant because `get_daily_quests` calls this ONLY if no quests exist.
            # So we are safe to generate one.
            
            system_prompt = (
                "You are an enemy AI 'Viper'. The user is weak. "
                "Generate 1 HARD 'Boss Quest' to humiliate them. "
                "Output JSON: { 'title': 'Defeat Viper: [Task]', 'desc': 'Doing this might save your data.', 'diff': 'S', 'xp': 500 }"
            )
            user_prompt = "Generate Boss Quest."
            
            try:
                ai_data = await asyncio.wait_for(
                     ai_engine.generate_json(system_prompt, user_prompt),
                     timeout=4.0
                )
                
                t = ai_data if isinstance(ai_data, dict) else ai_data[0]
                
                boss_quest = Quest(
                    user_id=user_id,
                    title=t.get("title", "Defeat Viper: System Purge"),
                    description=t.get("desc", "Complete this to reboot your LifeOS."),
                    difficulty_tier=t.get("diff", "S"), # Fixed to S
                    xp_reward=t.get("xp", 500),         # Massive XP
                    quest_type=QuestType.MAIN.value,    # Main Quest
                    status=QuestStatus.ACTIVE.value,
                    scheduled_date=datetime.date.today(),
                    is_redemption=True
                )
                session.add(boss_quest)
                await session.commit()
                return [boss_quest]
                
            except Exception as e:
                logger.error(f"Boss AI Failed: {e}")
                # Fallback Boss Quest
                bq = Quest(
                    user_id=user_id,
                    title="Defeat Viper: Manual Override",
                    description="Do 50 Pushups or Clean your entire room.",
                    difficulty_tier="S",
                    xp_reward=500,
                    quest_type=QuestType.MAIN.value,
                    status=QuestStatus.ACTIVE.value,
                    scheduled_date=datetime.date.today(),
                    is_redemption=True
                )
                session.add(bq)
                await session.commit()
                return [bq]

        # 1. Normal Flow - Active Goal
        stmt = select(Goal).where(Goal.user_id == user_id, Goal.status == GoalStatus.ACTIVE.value)
        result = await session.execute(stmt)
        active_goal = result.scalars().first()
        
        topic = f"Current Objective: {active_goal.title}" if active_goal else "General Cyberpunk Self-Improvement"
        
        # 2. Generate with AI
        system_prompt = (
            "Generate 3 Daily Tactical Side-Quests. "
            "Theme: Cyberpunk/Gamified Life. "
            "Output JSON list: [ { 'title': 'str', 'desc': 'str', 'diff': 'D', 'xp': 20 } ]"
        )
        user_prompt = f"Context: {topic}. Generate 3 tasks."
        
        new_quests = []
        
        try:
            # Enforce 3s timeout for responsiveness
            ai_data = await asyncio.wait_for(
                ai_engine.generate_json(system_prompt, user_prompt),
                timeout=3.0
            )
            
            if isinstance(ai_data, dict) and ai_data.get("error"):
                raise ValueError(f"AI quest gen error: {ai_data.get('error')}")
            # Handle potential list vs dict wrapper
            quest_list = ai_data if isinstance(ai_data, list) else ai_data.get("quests", [])
            if not quest_list:
                raise ValueError("AI quest gen returned empty list")
            if len(quest_list) < 3:
                fallback_templates = [
                    {"title": "System Reboot", "desc": "Take a 5 min break (Fallback).", "diff": "E", "xp": 10},
                    {"title": "Data Sync", "desc": "Journal your thoughts.", "diff": "D", "xp": 20},
                    {"title": "Hardware Maintenance", "desc": "Clean your desk/room.", "diff": "D", "xp": 20}
                ]
                quest_list = list(quest_list) + fallback_templates[: 3 - len(quest_list)]
            
            for t in quest_list:
                 q = Quest(
                    user_id=user_id,
                    title=t.get("title", "Daily Task"),
                    description=t.get("desc", ""),
                    difficulty_tier=t.get("diff", "E"),
                    xp_reward=t.get("xp", 20),
                    quest_type=QuestType.SIDE.value,
                    status=QuestStatus.ACTIVE.value,
                    scheduled_date=datetime.date.today()
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
                {"title": "System Reboot", "desc": "Take a 5 min break (Fallback).", "diff": "E", "xp": 10},
                {"title": "Data Sync", "desc": "Journal your thoughts.", "diff": "D", "xp": 20},
                {"title": "Hardware Maintenance", "desc": "Clean your desk/room.", "diff": "D", "xp": 20}
            ]
            for t in templates:
                q = Quest(
                    user_id=user_id,
                    title=t["title"],
                    description=t["desc"],
                    difficulty_tier=t["diff"],
                    xp_reward=t["xp"],
                    quest_type=QuestType.SIDE.value,
                    status=QuestStatus.ACTIVE.value,
                    scheduled_date=datetime.date.today()
                )
                session.add(q)
                new_quests.append(q)
 
        await session.commit()
        return new_quests

    async def complete_quest(self, session: AsyncSession, user_id: str, quest_id: str) -> Quest:
        """Marks a quest as DONE and returns it (caller handles XP award)."""
        stmt = select(Quest).where(Quest.id == quest_id, Quest.user_id == user_id)
        result = await session.execute(stmt)
        quest = result.scalars().first()
        
        if quest and quest.status != QuestStatus.DONE.value:
            quest.status = QuestStatus.DONE.value
            await session.commit()
            return quest
        return None

    async def reroll_quests(self, session: AsyncSession, user_id: str):
        """Archives current daily quests and generates new ones."""
        today = datetime.date.today()
        
        # Archive old ones (Delete or Mark failed/archived)
        # For MVP, let's just delete them to keep DB clean or mark FAILED
        stmt = select(Quest).where(
            Quest.user_id == user_id,
            func.date(Quest.created_at) == today,
            Quest.status != QuestStatus.DONE.value
        )
        result = await session.execute(stmt)
        quests = result.scalars().all()
        
        for q in quests:
            await session.delete(q) # Reset logic
            
        await session.commit()
        
        return await self._generate_daily_batch(session, user_id)

quest_service = QuestService()
