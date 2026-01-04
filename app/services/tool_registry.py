from app.services.user_service import user_service
from app.services.inventory_service import inventory_service
from app.services.quest_service import quest_service
from app.services.rival_service import rival_service
from app.services.flex_renderer import flex_renderer
from linebot.v3.messaging import TextMessage
import logging

logger = logging.getLogger(__name__)

class ToolRegistry:
    """
    Exposes a unified interface for the AI to call system functions.
    Each tool returns a tuple: (result_data: dict, reply_message: Message)
    """

    @staticmethod
    async def get_status(session, user_id: str):
        """Fetches User Profile."""
        user = await user_service.get_user(session, user_id)
        if not user:
            return {"error": "User not found"}, TextMessage(text="⚠️ User undefined.")
        
        msg = flex_renderer.render_status(user)
        return {"status": "success", "level": user.level}, msg

    @staticmethod
    async def get_inventory(session, user_id: str):
        """Fetches User Inventory."""
        items = await inventory_service.get_user_inventory(session, user_id)
        if not items:
            return {"count": 0}, TextMessage(text="🎒 Inventory is empty.")
        
        item_list = "\n".join([f"- {ui.item.name} x{ui.quantity}" for ui in items])
        # In a real app, this would be a Flex Message Grid
        msg = TextMessage(text=f"🎒 **INVENTORY** 🎒\n{item_list}")
        return {"count": len(items), "items": [i.item.name for i in items]}, msg

    @staticmethod
    async def get_quests(session, user_id: str):
        """Fetches Daily Quests."""
        quests = await quest_service.get_daily_quests(session, user_id)
        msg = flex_renderer.render_quest_list(quests)
        return {"count": len(quests)}, msg

    @staticmethod
    async def use_item(session, user_id: str, item_name: str):
        """Uses an item by fuzzy name matching."""
        result_text = await inventory_service.use_item(session, user_id, item_name)
        return {"result": result_text}, TextMessage(text=result_text)

    @staticmethod
    async def log_action(session, user_id: str, text: str):
        """Standard RPG Action Logging."""
        result = await user_service.process_action(session, user_id, text)
        msg = flex_renderer.render(result)
        return result.dict(), msg
    
    @staticmethod
    async def set_goal(session, user_id: str, goal_text: str):
        """Sets a new macro goal."""
        goal, plan = await quest_service.create_new_goal(session, user_id, goal_text)
        
        milestone_txt = "\n".join([f"- {m['title']} ({m.get('difficulty','C')})" for m in plan.get("milestones", [])])
        msg_txt = f"🎯 **TACTICAL PLAN ACQUIRED**\nGoal: {goal.title}\n\n**Milestones Detected:**\n{milestone_txt}\n\nSystem is calibrating daily routines..."
        
        return {"goal": goal.title, "milestones": len(plan.get("milestones", []))}, TextMessage(text=msg_txt)

tool_registry = ToolRegistry()
