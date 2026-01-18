import logging
import datetime
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy import select
from application.services.ai_engine import ai_engine

logger = logging.getLogger(__name__)


class AgentSystemAction(BaseModel):
    action_type: str  # "DIFFICULTY_CHANGE", "PUSH_QUEST", "BRIDGE_GEN"
    details: Dict[str, Any]
    reason: str


class ExecutiveService:
    """
    Handles System-Level Judgment, Rules, and Automated Interventions.
    """

    async def execute_system_judgment(self, session, user_id: str) -> Optional[AgentSystemAction]:
        """
        The Autonomous Executive Loop.
        Analyzes performance metrics and decides on system-level interventions.
        """
        from application.services.quest_service import quest_service
        from app.models.quest import Quest, QuestStatus, Goal, GoalStatus

        # 1. Gather Metrics (Last 3 Days)
        stmt = select(Quest).where(Quest.user_id == user_id, Quest.status == QuestStatus.ACTIVE.value)
        active_quests = (await session.execute(stmt)).scalars().all()

        fail_streak = 0
        oldest_active = 0
        now = datetime.datetime.now()

        # Check staleness
        for q in active_quests:
            if q.created_at:
                created = q.created_at
                if created.tzinfo:
                    created = created.replace(tzinfo=None)
                age = (now - created).days
                if age > 2:
                    fail_streak += 1
                oldest_active = max(oldest_active, age)

        # 2. Judge (The Algorithm)
        if fail_streak >= 2:
            logger.info(f"Executive Judgment: User {user_id} is overwhelmed. Downgrading difficulty.")
            count = await quest_service.bulk_adjust_difficulty(session, user_id, target_tier="E")
            return AgentSystemAction(
                action_type="DIFFICULTY_CHANGE",
                details={"tier": "E", "count": count},
                reason="Overwhelm Detected (Stale Quests)",
            )

        # 3. Momentum Check (Last Active)
        if not active_quests:
            pass

        # 4. Goal Stagnation Check (The Bridge)
        stmt = select(Goal).where(Goal.user_id == user_id, Goal.status == GoalStatus.ACTIVE.value)
        active_goals = (await session.execute(stmt)).scalars().all()

        for goal in active_goals:
            q_stmt = select(Quest).where(Quest.goal_id == goal.id).order_by(Quest.created_at.desc()).limit(1)
            last_quest = (await session.execute(q_stmt)).scalars().first()

            days_since = 999
            if last_quest and last_quest.created_at:
                created = last_quest.created_at
                if created.tzinfo:
                    created = created.replace(tzinfo=None)
                days_since = (now - created).days
            elif goal.created_at:
                created = goal.created_at
                if created.tzinfo:
                    created = created.replace(tzinfo=None)
                days_since = (now - created).days

            if days_since > 30:
                logger.warning(
                    f"Executive Judgment: Goal {goal.title} ignored for {days_since}d. TRIGGERING CHECKMATE."
                )
                return AgentSystemAction(
                    action_type="PUSH_QUEST",
                    details={"title": f"BOSS: Reclaim {goal.title}", "diff": "S", "type": "REDEMPTION"},
                    reason=f"CHECKMATE (Goal ignored {days_since} days)",
                )

            if days_since > 7:
                logger.info(f"Executive Judgment: Goal {goal.title} is stagnant ({days_since}d). Building Bridge.")
                bridge_quest = await quest_service.create_bridge_quest(session, user_id, goal.id)
                if bridge_quest:
                    return AgentSystemAction(
                        action_type="BRIDGE_GEN",
                        details={"quest_title": bridge_quest.title, "goal": goal.title},
                        reason=f"Goal Stagnation ({days_since} days)",
                    )

        # 5. Reality Sync
        external_load = await self._get_external_load(user_id)
        if external_load > 0.8:
            logger.info("Executive Judgment: External High Load detected. Adjusting difficulty.")
            count = await quest_service.bulk_adjust_difficulty(session, user_id, target_tier="E")
            return AgentSystemAction(
                action_type="DIFFICULTY_CHANGE",
                details={"tier": "E", "source": "CALENDAR_SYNC"},
                reason="High External Load",
            )

        return None

    async def _get_external_load(self, user_id: str) -> float:
        """Stub for Google/Outlook Calendar integration."""
        return 0.0

    async def judge_reroll_request(self, session, user_id: str, reason: str) -> dict:
        """
        F6: AI judges if a quest reroll request is valid.
        """
        try:
            result = await ai_engine.generate_json(
                """You are a strict task arbiter. User wants to skip/reroll a quest.
Judge if the excuse is VALID (legitimate) or INVALID (lazy).
Output JSON: {"approved": true/false, "verdict": "Brief explanation in Traditional Chinese"}
Examples of VALID: "I have an urgent work meeting", "Medical emergency"
Examples of INVALID: "I don't feel like it", "Too tired", "Lazy"
""",
                f"User's excuse: {reason}",
            )
            return {"approved": result.get("approved", False), "verdict": result.get("verdict", "系統無法判斷。")}
        except Exception as e:
            logger.error(f"Reroll judgment failed: {e}")
            return {"approved": False, "verdict": "系統錯誤，默認拒絕。"}

    async def initiate_tribunal(self, session, user_id: str, charge: str, penalty_xp: int = 100) -> dict:
        """
        F8: Creates a penalty tribunal where user must plead.
        """
        import uuid

        session_id = str(uuid.uuid4())[:8]
        return {
            "session_id": session_id,
            "charge": charge,
            "max_penalty": penalty_xp,
            "options": ["認罪 (Guilty)", "無罪抗辯 (Not Guilty)"],
        }
