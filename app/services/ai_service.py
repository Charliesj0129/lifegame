from app.services.ai_engine import ai_engine
from app.services.tool_registry import tool_registry
from app.services.user_service import user_service
from app.services.rival_service import rival_service
from linebot.v3.messaging import TextMessage
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
        The Core Loop (v2.0 AI-Native):
        1. Parse Fuzzy Intent & Chain of Thought
        2. Execute Single or Multiple Tools
        3. Return Final Response
        """
        # 1. Gather Context
        user = await user_service.get_or_create_user(session, user_id)
        rival = await rival_service.get_or_create_rival(session, user_id)
        history = await AIService._get_history(session, user_id)
        
        # 2. Enhanced System Prompt
        context_str = f"""
Current User State:
- Level: {user.level} (Streak: {user.streak_count})
- Rival: Lv.{rival.level} ({'Active' if rival.level >= user.level else 'Dormant'})
- HP: {user.hp}/{user.max_hp}

Recent History:
{history}
"""
        
        system_prompt = f"""Role: LifeOS Gamification Manager (v2.0).
{context_str}

Available Tools:
- get_status() : View stats
- get_inventory() : View items
- get_quests() : View active tasks
- use_item(item_name: str) : Consume item
- set_goal(goal_text: str) : Create specific goal
- log_action(text: str) : Log habit/action (Default)
- give_advice(topic: str) : Provide empathy/tactical advice (for fuzzy inputs like "I'm tired")

Task: Analyze input. Return JSON.
Support Chain of Thought (CoT): If user asks for multiple things (e.g. "Drink potion then sleep"), return a LIST of actions.
Language: ALWAYS use Traditional Chinese (繁體中文) for any text output or reasoning that might be visible.

Schema (Single):
{{ "thought": "str (Traditional Chinese)", "tool": "tool_name", "arguments": {{...}} }}

Schema (Chain):
{{ "thought": "str (Traditional Chinese)", "plan": [ {{ "tool": "tool_name", "arguments": {{...}} }}, ... ] }}
"""
        # Save User Input
        await AIService._save_log(session, user_id, "user", user_text)

        # 3. AI Inference
        final_msg = None
        main_tool_name = "unknown"
        final_data = {}
        
        try:
            ai_resp = await ai_engine.generate_json(system_prompt, user_text)
            
            # Normalize to List of Actions
            actions = []
            if isinstance(ai_resp, dict):
                if "plan" in ai_resp:
                    actions = ai_resp["plan"]
                else:
                    actions = [ai_resp]
            elif isinstance(ai_resp, list):
                actions = ai_resp
            
            logger.info(f"AI Router Plan: {len(actions)} steps. {actions}")
            
            # 4. Execution Loop
            results = []
            for act in actions:
                tool = act.get("tool", "log_action")
                args = act.get("arguments") or {}
                
                # Update main tool name for logging/return (use last significant one)
                main_tool_name = tool
                
                if tool == "get_status":
                    data, msg = await tool_registry.get_status(session, user_id)
                    results.append(msg)
                    final_data = data
                elif tool == "get_inventory":
                    data, msg = await tool_registry.get_inventory(session, user_id)
                    results.append(msg)
                elif tool == "get_quests":
                    data, msg = await tool_registry.get_quests(session, user_id)
                    results.append(msg)
                elif tool == "use_item":
                    data, msg = await tool_registry.use_item(session, user_id, args.get("item_name", "unknown"))
                    results.append(msg)
                elif tool == "set_goal":
                    data, msg = await tool_registry.set_goal(session, user_id, args.get("goal_text", user_text))
                    results.append(msg)
                elif tool == "give_advice":
                    # Special Tool: Just return text advice? Or use a renderer?
                    # For now, let's just Log it as an action but with specific formatting?
                    # Or simple TextMessage.
                    topic = args.get("topic", "General")
                    advice_text = f"💡 建議：{topic}。先休息，補充精神值。"
                    msg = TextMessage(text=advice_text)
                    results.append(msg)
                    final_data = {"advice": topic}
                else:
                    # log_action
                    txt = args.get("text", user_text)
                    data, msg = await tool_registry.log_action(session, user_id, txt)
                    results.append(msg)
                    final_data = data

            # 5. response aggregation (If multiple messages, how to send?)
            # Webhook expects Single Message usually. 
            # If multiple, we might need to return a list? 
            # Existing webhook.py handles: response_message = TextMessage or FlexContainer.
            # It sends `line_bot_api.reply_message`. reply_message supports LIST of messages (up to 5).
            # So we should return a LIST of messages if possible, or composite.
            
            # But the signature expected by webhook is `response_message, intent_tool, result_data`.
            # If `response_message` is a list, we need to check if webhook handles it.
            # Let's check webhook.py next. For now, let's return the LAST parsed message, 
            # OR a special "MultiMessage" if supported.
            # Actually, `reply_message` takes `messages=[]`. 
            # If we change the return type to List[Message], we must update webhook.py.
            # To keep it simple for now: Return the LAST one, but if multiple, maybe combine text?
            
            if len(results) > 1:
                # Combine standard text messages
                combined_text = ""
                flex_msg = None
                for res in results:
                    if isinstance(res, TextMessage):
                        combined_text += f"{res.text}\n"
                    else:
                        flex_msg = res # Keep the last flex
                
                if flex_msg:
                    final_msg = flex_msg # Prioritize Flex (UI)
                else:
                    final_msg = TextMessage(text=combined_text.strip())
            elif results:
                final_msg = results[0]
            else:
                final_msg = TextMessage(text="...")
            
            # Log Response
            resp_log = getattr(final_msg, 'text', '[Complex Message]')
            await AIService._save_log(session, user_id, "assistant", resp_log)
            
            return final_msg, main_tool_name, final_data

        except Exception as e:
            logger.error(f"Router Fail: {e}", exc_info=True)
            # Fallback
            try:
                result_data, msg = await tool_registry.log_action(session, user_id, user_text)
                return msg, "fallback_log", result_data
            except Exception as fallback_error:
                logger.error(f"Fallback log_action failed: {fallback_error}", exc_info=True)
                return TextMessage(text="⚠️ 系統異常：行動未記錄，請查看日誌。"), "fallback_error", {}

ai_router = AIService()
