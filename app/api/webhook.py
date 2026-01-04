from fastapi import APIRouter, Request, Header, HTTPException
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import AsyncApiClient, AsyncMessagingApi, ReplyMessageRequest, TextMessage, ShowLoadingAnimationRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from app.services.line_bot import get_line_handler, get_messaging_api
from app.services.ai_engine import ai_engine
from app.services.flex_renderer import flex_renderer
from app.services.persona_service import persona_service
from app.services.audio_service import audio_service
import logging

router = APIRouter()
logger = logging.getLogger("lifgame")

@router.post("/callback")
async def callback(request: Request, x_line_signature: str = Header(None)):
    if x_line_signature is None:
         raise HTTPException(status_code=400, detail="Missing X-Line-Signature header")

    body = await request.body()
    body_str = body.decode('utf-8')
    
    handler = get_line_handler()

    try:
        await handler.handle(body_str, x_line_signature)
    except InvalidSignatureError:
        logger.error("Invalid Line signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    return "OK"

# Event Handlers
# We need to register these *after* the handler is created, or expose a setup function.
# Since handler is global helper, we can register here at import time (module level) 
# but we need to ensure handler IS instantiated.
# A pattern is to do it in main or here if we are sure it's imported.
# Let's do it here for simplicity, calling get_line_handler().

webhook_handler = get_line_handler()

from app.services.user_service import user_service
from app.services.inventory_service import inventory_service
from app.api.deps import get_db
import app.core.database
from app.services.quest_service import quest_service

from app.services.rival_service import rival_service

# ... (Previous imports)

@webhook_handler.add(MessageEvent, message=TextMessageContent)
async def handle_message(event: MessageEvent):
    user_text = event.message.text
    user_id = event.source.user_id
    reply_token = event.reply_token

    # 1. Trigger Loading Animation (mask latency)
    try:
        api = get_messaging_api()
        if api:
             # Loading limit is 5s-60s. Default is enough.
             await api.show_loading_animation(
                 ShowLoadingAnimationRequest(chat_id=user_id, loading_seconds=10)
             )
    except Exception as e:
        logger.warning(f"Could not show loading animation: {e}")

    # Execute Logic
    response_message = TextMessage(text="System Error")
    sender_persona = persona_service.SYSTEM
    rival_log = ""

    try:
        async with app.core.database.AsyncSessionLocal() as session:
            # 1. Get User (Required for Rival Check)
            user = await user_service.get_or_create_user(session, user_id)
            
            # 2. Nemesis System: Check Inactivity & Penalties
            try:
                rival_log = await rival_service.process_encounter(session, user)
            except Exception as e:
                logger.warning(f"Rival encounter failed: {e}")
            
            # Command Handling
            if user_text.strip().lower() == "status":
                # user is already fetched above
                try:
                    response_message = flex_renderer.render_status(user)
                    sender_persona = persona_service.SYSTEM
                except Exception as e:
                    logger.error(f"Flex Render Failed: {e}", exc_info=True)
                    response_message = TextMessage(text=f"⚠️ Status Render Error: {e}")
                    sender_persona = persona_service.SYSTEM

            elif user_text.strip().lower() == "inventory":
                items = await inventory_service.get_user_inventory(session, user_id)
                if not items:
                    response_message = TextMessage(text="🎒 Inventory is empty.")
                else:
                    item_list = "\n".join([f"- {ui.item.name} x{ui.quantity}" for ui in items])
                    response_message = TextMessage(text=f"🎒 **INVENTORY** 🎒\n{item_list}")
                sender_persona = persona_service.SYSTEM

            elif user_text.strip().lower() == "quests":
                quests = await quest_service.get_daily_quests(session, user_id)
                response_message = flex_renderer.render_quest_list(quests)
                sender_persona = persona_service.SYSTEM
            
            elif user_text.strip().lower().startswith("use "):
                item_keyword = user_text.strip()[4:]
                result_text = await inventory_service.use_item(session, user_id, item_keyword)
                response_message = TextMessage(text=result_text)
                sender_persona = persona_service.MENTOR # Guidance Persona

            elif user_text.strip().lower().startswith("/new_goal ") or user_text.strip().lower().startswith("goal: "):
                # Extract Goal
                if user_text.startswith("/new_goal"):
                    goal_text = user_text[10:].strip()
                else:
                    goal_text = user_text[6:].strip()
                
                # Call Quest Service
                goal, plan = await quest_service.create_new_goal(session, user_id, goal_text)
                
                # Render Response
                milestone_txt = "\n".join([f"- {m['title']} ({m.get('difficulty','C')})" for m in plan.get("milestones", [])])
                msg_txt = f"🎯 **TACTICAL PLAN ACQUIRED**\nGoal: {goal.title}\n\n**Milestones Detected:**\n{milestone_txt}\n\nSystem is calibrating daily routines..."
                response_message = TextMessage(text=msg_txt)
                sender_persona = persona_service.MENTOR

            else:
                # Regular Action (RPG Log)
                result = await user_service.process_action(session, user_id, user_text)
                response_message = flex_renderer.render(result)
                sender_persona = persona_service.SYSTEM 
            
    except Exception as e:
        logger.error(f"Error processing action: {e}", exc_info=True)
        response_message = TextMessage(text="⚠️ System Glitch: Action not logged. Check logs.")

    # Attach Sender
    response_message.sender = persona_service.get_sender_object(sender_persona)

    # Audio Fanfare (Level Up) & Reply Preparation
    messages_to_send = []
    
    # Add Rival Log if exists
    if rival_log:
         viper_msg = TextMessage(text=rival_log)
         viper_msg.sender = persona_service.get_sender_object(persona_service.VIPER)
         messages_to_send.append(viper_msg)

    messages_to_send.append(response_message)
    
    if 'result' in locals() and hasattr(result, 'leveled_up') and result.leveled_up:
         fanfare = audio_service.get_level_up_audio()
         messages_to_send.append(fanfare)

    # Reply
    try:
        api = get_messaging_api()
        if api:
            logger.info(f"Attempting to reply with token: {reply_token}...")
            await api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=messages_to_send
                )
            )
            logger.info("Reply sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send reply: {e}", exc_info=True)
        # We don't raise here, so Line gets 200 OK and doesn't retry endlessly if it's a logic error.
        # But if it's a token expiry, we can't do much.

from linebot.v3.webhooks import MessageEvent, TextMessageContent, PostbackEvent, FollowEvent
from app.services.rich_menu_service import rich_menu_service

# ... (Previous imports and handlers)

@webhook_handler.add(FollowEvent)
async def handle_follow(event: FollowEvent):
    user_id = event.source.user_id
    logger.info(f"New Follower: {user_id}")
    
    # 1. Register User in DB (Optional, usually handled on first message, but good to do here)
    try:
        async with app.core.database.AsyncSessionLocal() as session:
             await user_service.get_or_create_user(session, user_id)
    except Exception as e:
        logger.error(f"Failed to create user on follow: {e}")

    # 2. Link Default Rich Menu
    rich_menu_service.link_user(user_id, "MAIN")

@webhook_handler.add(PostbackEvent)
async def handle_postback(event: PostbackEvent):
    user_id = event.source.user_id
    data = event.postback.data
    reply_token = event.reply_token
    
    logger.info(f"Received Postback from {user_id}: {data}")

    # Parse Query String style data (e.g. action=equip&item_id=123)
    # Simple parsing:
    params = {}
    for part in data.split('&'):
        if '=' in part:
            k, v = part.split('=', 1)
            params[k] = v
            
    action = params.get('action')
    response_text = "Action received."
    
    try:
        async with app.core.database.AsyncSessionLocal() as session:
            messages = []
            
            if action == "reroll_quests":
                quests = await quest_service.reroll_quests(session, user_id)
                messages.append(flex_renderer.render_quest_list(quests))
                response_text = "Quests Rerolled." # Fallback log
                
            elif action == "complete_quest":
                quest_id = params.get('quest_id')
                user = await user_service.get_or_create_user(session, user_id)
                quest = await quest_service.complete_quest(session, user_id, quest_id)
                
                if quest:
                    # Award XP
                    user.xp = (user.xp or 0) + quest.xp_reward
                    await session.commit()
                    messages.append(TextMessage(text=f"✅ Quest Completed! +{quest.xp_reward} XP"))
                else:
                    messages.append(TextMessage(text="⚠️ Quest already done or invalid."))

            elif action == "accept_all_quests":
                response_text = "✅ All Quests Accepted! (Mock)"
                messages.append(TextMessage(text=response_text))
                
            elif action == "skip_rival_update":
                response_text = "⏭️ Viper update skipped."
                messages.append(TextMessage(text=response_text))
                
            elif action == "equip":
                item_id = params.get('item_id')
                response_text = f"⚔️ Equipping Item {item_id}..."
                messages.append(TextMessage(text=response_text))
            
            else:
                response_text = f"Unknown Action: {action}"
                messages.append(TextMessage(text=response_text))
            
    except Exception as e:
        logger.error(f"Postback Error: {e}")
        response_text = "⚠️ Error processing request."

    # "Silent" Reply logic? 
    # Line requires a 200 OK and ideally a reply token usage or it might retry? 
    # Actually we MUST reply or the user sees nothing (loading spinner stops eventually but it's bad UX).
    # We reply with a ephemeral TextMessage or a Flex update.
    
    try:
        api = get_messaging_api()
        if api and 'messages' in locals() and messages:
            await api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=messages
                )
            )
        elif api:
             await api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=response_text)]
                )
            )
    except Exception as e:
        logger.error(f"Failed to reply to postback: {e}")
