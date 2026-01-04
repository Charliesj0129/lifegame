import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.services.ai_engine import ai_engine
from app.models.quest import Goal, Quest, GoalStatus, QuestStatus, QuestType

logger = logging.getLogger(__name__)

class GoalDecomposerService:
    def __init__(self):
        self.ai = ai_engine

    async def decompose_and_save(self, session: AsyncSession, user_id: str, goal_text: str) -> Goal:
        """
        1. Call AI to breakdown goal.
        2. Create Goal record.
        3. Create Quest records.
        """
        SYSTEM_PROMPT = """
        You are a Tactical Strategy AI (LifeOS).
        Your mission is to break down the user's vague goal into a concrete 'Quest Tree' based on 'Atomic Habits' principles.
        
        Output MUST be valid JSON with this structure:
        {
            "main_quest_title": "The epic title of the goal",
            "narrative_briefing": "A short, immersive cyberpunk briefing explaining the mission.",
            "sub_quests": [
                {
                    "title": "Actionable task title",
                    "type": "MAIN" | "SIDE",
                    "difficulty": "E" | "D" | "C" | "B" | "A" | "S",
                    "xp_reward": 50,
                    "schedule_offset_days": 0 
                }
            ]
        }
        
        Rules:
        1. Break it down into 3-5 sub-quests.
        2. At least one quest must be doable TODAY (offset 0).
        3. Use RPG terminology tailored to the goal.
        """
        
        # 1. AI Analysis
        prompt = f"Goal: {goal_text}"
        MAX_RETRIES = 2
        
        for attempt in range(MAX_RETRIES):
            try:
                response_json = await self.ai.generate_json(SYSTEM_PROMPT, prompt)
                if "error" in response_json:
                    logger.error(f"AI Generation Error: {response_json['error']}")
                    continue # Retry
                
                # 2. Parse and Create Goal
                goal = Goal(
                    user_id=user_id,
                    title=response_json.get("main_quest_title", goal_text),
                    description=response_json.get("narrative_briefing", ""),
                    status=GoalStatus.ACTIVE.value,
                    decomposition_json=response_json
                )
                session.add(goal)
                await session.flush() # Get goal.id
                
                # 3. Create Sub-Quests
                sub_quests = response_json.get("sub_quests", [])
                for idx, sq in enumerate(sub_quests):
                    # Calculate date based on offset
                    # For now, just simplistic mapping
                    is_today = (sq.get("schedule_offset_days", 1) == 0) or (idx == 0)
                    
                    quest = Quest(
                        goal_id=goal.id,
                        user_id=user_id,
                        title=sq.get("title", f"Step {idx+1}"),
                        difficulty_tier=sq.get("difficulty", "C"),
                        quest_type=QuestType.MAIN.value,
                        status=QuestStatus.ACTIVE.value if is_today else QuestStatus.PENDING.value,
                        xp_reward=sq.get("xp_reward", 50),
                        is_redemption=False
                        # scheduled_date TBD via logic, set later
                    )
                    session.add(quest)
                
                await session.commit()
                await session.refresh(goal)
                return goal
                
            except Exception as e:
                logger.error(f"Goal Decomposition Logic Failed: {e}", exc_info=True)
                if attempt == MAX_RETRIES - 1:
                    raise e
        return None

goal_decomposer = GoalDecomposerService() 

    # .... WRITING SKELETON FIRST ....
