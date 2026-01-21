import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from application.services.brain.advisor_service import AdvisorService
from application.services.brain.executive_service import AgentSystemAction, ExecutiveService
from application.services.brain.narrator_service import AgentPlan, AgentStatUpdate, NarratorService

logger = logging.getLogger(__name__)


class BrainService:
    """
    FACADE Service.
    The Executive Function of the Cyborg.
    Orchestrates Context -> Flow -> AI -> Plan.
    Delegates to:
    - NarratorService (Speech, Persona)
    - ExecutiveService (Rules, Judgment)
    - AdvisorService (Coaching, Reports)
    """

    def __init__(self):
        self.narrator = NarratorService()
        self.executive = ExecutiveService()
        self.advisor = AdvisorService()

    async def think(self, context: str = None, prompt: str = None, **kwargs) -> str:
        """Delegate to Narrator."""
        return await self.narrator.think(context, prompt, **kwargs)

    async def think_with_session(self, session, user_id: str, user_text: str, pulsed_events: Dict = None) -> AgentPlan:
        """Delegate to Narrator (Main Thought Loop)."""
        return await self.narrator.think_with_session(session, user_id, user_text, pulsed_events)

    async def execute_system_judgment(self, session, user_id: str) -> Optional[AgentSystemAction]:
        """Delegate to Executive."""
        return await self.executive.execute_system_judgment(session, user_id)

    async def judge_reroll_request(self, session, user_id: str, reason: str) -> dict:
        """Delegate to Executive."""
        return await self.executive.judge_reroll_request(session, user_id, reason)

    async def initiate_tribunal(self, session, user_id: str, charge: str, penalty_xp: int = 100) -> dict:
        """Delegate to Executive."""
        return await self.executive.initiate_tribunal(session, user_id, charge, penalty_xp)

    async def generate_weekly_report(self, session, user_id: str) -> dict:
        """Delegate to Advisor."""
        return await self.advisor.generate_weekly_report(session, user_id)

    async def suggest_habit_stack(self, session, user_id: str) -> str:
        """Delegate to Advisor."""
        return await self.advisor.suggest_habit_stack(session, user_id)


brain_service = BrainService()
