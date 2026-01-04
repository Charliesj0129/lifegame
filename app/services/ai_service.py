from app.services.ai_engine import ai_engine
from app.services.tool_registry import tool_registry
from app.services.user_service import user_service
from app.services.rival_service import rival_service
import logging
import json

logger = logging.getLogger(__name__)

from app.models.conversation_log import ConversationLog
from sqlalchemy import select, desc

class AIService:
    """
    Phase 4 Brain: Handles Intent Routing and Tool Execution with Memory.
    """

    @staticmethod
    async def _save_log(session, user_id: str, role: str, content: str):
        """Persist chat log."""
        try:
            log = ConversationLog(user_id=user_id, role=role, content=content)
            session.add(log)
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to save chat log: {e}")

    @staticmethod
    async def _get_history(session, user_id: str, limit: int = 3) -> str:
        """Fetch last N turns for context injection."""
        try:
            stmt = select(ConversationLog).filter_by(user_id=user_id).order_by(desc(ConversationLog.created_at)).limit(limit)
            result = await session.execute(stmt)
            logs = result.scalars().all()
            # Reverse to chronological order
            history_text = "\n".join([f"{log.role}: {log.content}" for log in reversed(logs)])
            return history_text if history_text else "No recent history."
        except Exception as e:
            logger.error(f"Failed to fetch history: {e}")
            return "History unavailable."

    @staticmethod
    async def router(session, user_id: str, user_text: str):
        """
        The Core Loop:
        1. Fetch Context (User State + Rival + History)
        2. Prompt AI for Intent (JSON)
        3. Execute Tool
        4. Return Response Message
        """
        # 1. Gather Context
        user = await user_service.get_or_create_user(session, user_id)
        rival = await rival_service.get_or_create_rival(session, user_id)
        history = await AIService._get_history(session, user_id)
        
        # 2. Construct System Prompt
        context_str = f"""
Current User State:
- Level: {user.level} (Streak: {user.streak_count})
- Rival (Viper): Lv.{rival.level} (Status: {"Active" if rival.level >= user.level else "Dormant"})

Recent Conversation History:
{history}
"""
        
        system_prompt = f"""Role: LifeOS Gamification Manager.
{context_str}

Available Tools:
- get_status() : View stats
- get_inventory() : View items
- get_quests() : View missions
- use_item(item_name: str) : Consume item
- set_goal(goal_text: str) : Define objective
- log_action(text: str) : Default RPG log behavior

Task: Analyze input. Return JSON.
Schema:
{{
  "thought": "Reasoning string",
  "tool": "get_status" | "get_inventory" | "get_quests" | "use_item" | "set_goal" | "log_action",
  "arguments": {{ ...key-value pairs... }}
}}
"""
        # Save User Input immediately
        await AIService._save_log(session, user_id, "user", user_text)

        # 3. AI Inference
        msg = None
        tool_name = "unknown"
        result_data = {}
        
        try:
            intent = await ai_engine.generate_json(system_prompt, user_text)
            
            tool_name = intent.get("tool", "log_action")
            args = intent.get("arguments", {})
            
            logger.info(f"AI Router Decision: {tool_name} | Args: {args}")
            
            # 4. Dispatch
            if tool_name == "get_status":
                result_data, msg = await tool_registry.get_status(session, user_id)
                
            elif tool_name == "get_inventory":
                result_data, msg = await tool_registry.get_inventory(session, user_id)
            
            elif tool_name == "get_quests":
                result_data, msg = await tool_registry.get_quests(session, user_id)
                
            elif tool_name == "use_item":
                item_name = args.get("item_name", "unknown")
                result_data, msg = await tool_registry.use_item(session, user_id, item_name)
                
            elif tool_name == "set_goal":
                goal_text = args.get("goal_text", user_text)
                result_data, msg = await tool_registry.set_goal(session, user_id, goal_text)
                
            else:
                # Default / log_action
                action_text = args.get("text", user_text) 
                result_data, msg = await tool_registry.log_action(session, user_id, action_text)
                
            # 5. Log Response (for Context Loop)
            response_text = "[Flex/Image]"
            if hasattr(msg, "text") and msg.text:
                response_text = msg.text
            elif tool_name == "get_status":
                response_text = "[Displayed Status Dashboard]"
            
            await AIService._save_log(session, user_id, "assistant", response_text)
                
            return msg, tool_name, result_data

        except Exception as e:
            logger.error(f"Router Fail: {e}", exc_info=True)
            # Fallback
            result_data, msg = await tool_registry.log_action(session, user_id, user_text)
            return msg, "fallback_log", result_data

ai_router = AIService()
