from legacy.services.user_service import user_service
from legacy.services.inventory_service import inventory_service
from legacy.services.quest_service import quest_service
from legacy.services.lore_service import lore_service
from legacy.services.flex_renderer import flex_renderer
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
            return {"error": "User not found"}, TextMessage(text="⚠️ 使用者不存在。")

        lore_prog = await lore_service.get_user_progress(session, user_id)
        msg = flex_renderer.render_status(user, lore_prog)
        return {"status": "success", "level": user.level}, msg

    @staticmethod
    async def get_inventory(session, user_id: str):
        """Fetches User Inventory."""
        items = await inventory_service.get_user_inventory(session, user_id)
        if not items:
            return {"count": 0}, TextMessage(text="🎒 背包是空的。")

        item_list = "\n".join([f"- {ui.item.name} x{ui.quantity}" for ui in items])
        # In a real app, this would be a Flex Message Grid
        msg = TextMessage(text=f"🎒 背包清單\n{item_list}")
        return {"count": len(items), "items": [i.item.name for i in items]}, msg

    @staticmethod
    async def get_quests(session, user_id: str):
        """Fetches Daily Quests and Habits."""
        quests = await quest_service.get_daily_quests(session, user_id)
        habits = await quest_service.get_daily_habits(session, user_id)
        msg = flex_renderer.render_quest_list(quests, habits)
        return {"count": len(quests)}, msg

    @staticmethod
    async def use_item(session, user_id: str, item_name: str):
        """Uses an item by fuzzy name matching."""
        result_text = await inventory_service.use_item(session, user_id, item_name)
        from legacy.services.flex_renderer import flex_renderer
        from legacy.models.lore import LoreEntry

        if isinstance(result_text, LoreEntry):
            msg = flex_renderer.render_lore_shard(result_text)
            return {"result": "lore_unlocked", "title": result_text.title}, msg
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

        milestones = (
            plan.get("milestones")
            or plan.get("tactical_quests")
            or plan.get("micro_missions")
            or []
        )
        habits = plan.get("daily_habits", [])

        msg = flex_renderer.render_plan_confirmation(goal.title, milestones, habits)

        return {"goal": goal.title, "milestones": len(milestones)}, msg


tool_registry = ToolRegistry()
