import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timezone, timedelta

from adapters.persistence.kuzu.adapter import get_kuzu_adapter
from legacy.models.action_log import ActionLog
from app.models.user import User

logger = logging.getLogger(__name__)


class ContextService:
    def __init__(self):
        self.kuzu = get_kuzu_adapter()

    async def get_working_memory(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """
        Assemble the Working Memory for the Brain.
        Returns:
            {
                "short_term_history": str,  # Last 5 actions
                "long_term_context": List[Dict], # Graph data
                "user_state": Dict, # Churn risk, current goal
                "time_context": str # Current time, streak
            }
        """
        # 1. Short Term History (SQL)
        short_term_logs = await self._get_recent_actions(session, user_id)
        short_term_str = "\n".join([f"- {log.action_text} ({log.timestamp})" for log in short_term_logs])

        # 2. Long Term Context (Graph)
        long_term_data = self.kuzu.query_recent_context(user_id, limit=5)

        # 3. User State & Time
        user_state = await self._get_user_state(session, user_id)
        # 4. Identity Context (Semantic Self)
        identity = self._get_identity_context(user_id)

        return {
            "short_term_history": short_term_str,
            "long_term_context": long_term_data,
            "user_state": user_state,
            "identity_context": identity,
            "time_context": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }

    async def _get_recent_actions(self, session: AsyncSession, user_id: str, limit: int = 5) -> List[ActionLog]:
        try:
            stmt = (
                select(ActionLog).where(ActionLog.user_id == user_id).order_by(desc(ActionLog.timestamp)).limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to fetch ActionLog: {e}")
            return []

    async def _get_user_state(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Calculate Motivation, Churn Risk (EOMM)."""
        try:
            stmt = select(User).where(User.id == user_id)
            user = (await session.execute(stmt)).scalars().first()
            if not user:
                return {}

            # Simple Churn Heuristic: Inactive > 2 days
            last_active = user.last_active_date or datetime.now(timezone.utc)
            days_inactive = (datetime.now(timezone.utc) - last_active).days
            churn_risk = "HIGH" if days_inactive > 2 else "LOW"

            return {
                "level": user.level,
                "current_hp": user.hp,
                "streak": user.streak_count or 0,
                "churn_risk": churn_risk,
            }
        except Exception as e:
            logger.error(f"Failed to fetch User State: {e}")
            return {}

    def _get_identity_context(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch semantic identity (Who am I?) and values (What matters?) from Graph.
        """
        try:
            # Placeholder: In future, use self.kuzu.query(...) to find (User)-[:VALUES]->(Value)
            return {
                "core_values": ["Growth", "Autonomy"],
                "identity_tags": ["Seeker", "Architect"]
            }
        except Exception:
            return {}

context_service = ContextService()
