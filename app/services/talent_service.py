from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.talent import TalentTree, UserTalent
from app.models.user import User
import uuid
import logging

logger = logging.getLogger(__name__)

class TalentService:
    async def get_talent_tree(self, session: AsyncSession, class_type: str = "GENERAL"):
        """Fetches all talents for a class type."""
        stmt = select(TalentTree).where(TalentTree.class_type == class_type).order_by(TalentTree.tier)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_user_talents(self, session: AsyncSession, user_id: str):
        """Fetches all talents unlocked by the user."""
        stmt = select(UserTalent).where(UserTalent.user_id == user_id, UserTalent.is_active == True)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def unlock_talent(self, session: AsyncSession, user_id: str, talent_id: str):
        """
        Unlocks or upgrades a talent.
        Checks:
        1. User has enough points.
        2. Prerequisites met (parent unlocked).
        3. Not max rank.
        """
        # 1. Fetch User & Talent
        user_stmt = select(User).where(User.id == user_id)
        user = (await session.execute(user_stmt)).scalars().first()
        
        talent_stmt = select(TalentTree).where(TalentTree.id == talent_id)
        talent = (await session.execute(talent_stmt)).scalars().first()
        
        if not user or not talent:
            return {"success": False, "message": "User or Talent not found"}
            
        # 2. Check Points
        if user.talent_points < talent.cost:
           return {"success": False, "message": f"Not enough points. Need {talent.cost}, have {user.talent_points}"}
           
        # 3. Check Prerequisites
        if talent.parent_id:
             # Check if user has parent
             parent_check = select(UserTalent).where(
                 UserTalent.user_id == user_id, 
                 UserTalent.talent_id == talent.parent_id
             )
             has_parent = (await session.execute(parent_check)).scalars().first()
             if not has_parent:
                 return {"success": False, "message": "Prerequisite talent not unlocked."}
                 
        # 4. Check Current Rank
        existing_stmt = select(UserTalent).where(
            UserTalent.user_id == user_id,
            UserTalent.talent_id == talent_id
        )
        existing = (await session.execute(existing_stmt)).scalars().first()
        
        if existing:
            if existing.current_rank >= talent.max_rank:
                return {"success": False, "message": "Talent already at max rank."}
            existing.current_rank += 1
        else:
            new_talent = UserTalent(
                id=str(uuid.uuid4()),
                user_id=user_id,
                talent_id=talent_id,
                current_rank=1
            )
            session.add(new_talent)
            
        # 5. Deduct Points & Apply Effect (Immediate effects if any, usually effects are passive calc)
        user.talent_points -= talent.cost
        
        await session.commit()
        return {"success": True, "message": f"Unlocked {talent.name}!"}

talent_service = TalentService()
