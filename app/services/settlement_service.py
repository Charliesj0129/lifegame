from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.action_log import ActionLog
from app.models.user import User
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class SettlementService:
    async def generate_weekly_report(self, session: AsyncSession, user_id: str) -> str:
        # Define "Week" as last 7 days
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        # Aggregate Query
        stmt = select(
            func.count(ActionLog.id).label("count"),
            func.sum(ActionLog.xp_gained).label("total_xp")
        ).where(
            ActionLog.user_id == user_id,
            ActionLog.timestamp >= seven_days_ago
        )
        result = await session.execute(stmt)
        stats = result.one()
        count = stats.count or 0
        total_xp = stats.total_xp or 0
        
        # Most trained attribute
        attr_stmt = select(
            ActionLog.attribute_tag,
            func.sum(ActionLog.xp_gained).label("attr_xp")
        ).where(
            ActionLog.user_id == user_id,
            ActionLog.timestamp >= seven_days_ago
        ).group_by(ActionLog.attribute_tag).order_by(func.sum(ActionLog.xp_gained).desc()).limit(1)
        
        attr_result = await session.execute(attr_stmt)
        top_attr = attr_result.first()
        top_attr_str = f"{top_attr.attribute_tag} ({top_attr.attr_xp} XP)" if top_attr else "None"
        
        # Generate Text Report (Can be upgraded to Flex)
        report = (
            f"📅 **Weekly Settlement** 📅\n"
            f"--------------------------\n"
            f"Actions Logged: {count}\n"
            f"Total XP Gained: {total_xp}\n"
            f"Main Focus: {top_attr_str}\n"
            f"--------------------------\n"
            f"Keep it up! Your legend grows."
        )
        return report

settlement_service = SettlementService()
