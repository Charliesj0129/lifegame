import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User

logger = logging.getLogger(__name__)


class ActionService:
    async def execute_actions(self, actions: List[Dict[str, Any]], db: AsyncSession):
        """
        Executes a list of actions determined by the brain.
        Example action: {"type": "MODIFY_HP", "target": "player", "amount": -5, "reason": "Doomscrolling"}
        """
        results = []

        # Pre-fetch user (assuming single player for now, or finding by ID 1 or a default)
        # In this minimal version, we assume user with id="1" or similar exists, given it's single player.
        # But `User` model has String ID (Line User ID). We might need to know WHO the user is.
        # For Cyborg Architecture/Single Player, maybe we hardcode a 'PLAYER_ONE' ID or get it from config.
        PLAYER_ID = "U_CYBORG_HOST"

        stmt = select(User).where(User.id == PLAYER_ID)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            # Create if not exists for this hybrid setup
            user = User(id=PLAYER_ID, name="Charlie", hp=100, max_hp=100)
            db.add(user)
            await db.flush()

        for action in actions:
            try:
                act_type = action.get("type")
                if act_type == "MODIFY_HP":
                    amount = action.get("amount")
                    reason = action.get("reason")

                    user.hp = max(0, min(user.hp + amount, user.max_hp))

                    logger.info(f"❤️ HP Change: {amount} ({reason}) -> Current: {user.hp}")
                    results.append(f"HP {'-' if amount < 0 else '+'}{abs(amount)} ({reason}) -> {user.hp}")

                elif act_type == "NPC_EMOTE":
                    npc = action.get("npc")
                    emote = action.get("emote")
                    logger.info(f"😠 {npc} is {emote}")
                    results.append(f"{npc} looks {emote}")

                else:
                    logger.warning(f"Unknown action: {act_type}")

            except Exception as e:
                logger.error(f"Action Execution Error: {e}")
                results.append(f"Error executing {action}: {e}")

        await db.commit()
        return results


action_service = ActionService()
