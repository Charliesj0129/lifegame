from fastapi import APIRouter, Request, Header, HTTPException
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ReplyMessageRequest, TextMessage, ShowLoadingAnimationRequest
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from app.services.line_bot import get_line_handler, get_messaging_api
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
import app.core.database
from app.services.quest_service import quest_service
from app.services.boss_service import boss_service
from app.services.shop_service import shop_service
from app.services.crafting_service import crafting_service
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
    result_data = {}

    try:
        async with app.core.database.AsyncSessionLocal() as session:
            # 1. Get User (Required for Rival Check)
            user = await user_service.get_or_create_user(session, user_id)
            
            # 2. Nemesis System: Check Inactivity & Penalties
            try:
                rival_log = await rival_service.process_encounter(session, user)
            except Exception as e:
                rival_log = await rival_service.process_encounter(session, user)
            except Exception as e:
                logger.warning(f"Rival encounter failed: {e}")
            
            # Manual Override for Shop (Phase 6)
            if "shop" in user_text.lower() or "store" in user_text.lower() or "market" in user_text.lower():
                items = await shop_service.list_shop_items(session)
                response_message = flex_renderer.render_shop_list(items, user.gold or 0)
                # Skip Router
                intent_tool = "shop"
            elif "craft" in user_text.lower() or "workshop" in user_text.lower():
                recipes = await crafting_service.get_available_recipes(session, user_id)
                response_message = flex_renderer.render_crafting_menu(recipes)
                intent_tool = "craft"
            elif "boss" in user_text.lower():
                boss = await boss_service.get_active_boss(session, user_id)
                if not boss:
                    msg = await boss_service.spawn_boss(session, user_id)
                    boss = await boss_service.get_active_boss(session, user_id)
                    # Ideally we show the msg then the status, but for now just status
                
                response_message = flex_renderer.render_boss_status(boss)
                intent_tool = "boss"
            elif "attack" in user_text.lower():
                challenge = await boss_service.generate_attack_challenge()
                # Create a simple confirmation button for the challenge
                # For MVP, just text with quick reply or button?
                # Let's use a Text Message with a Quick Reply for "DONE"
                from linebot.v3.messaging import QuickReply, QuickReplyItem, PostbackAction as LinePostbackAction
                response_message = TextMessage(
                    text=f"⚔️ BOSS CHALLENGE: {challenge}",
                    quick_reply=QuickReply(items=[
                        QuickReplyItem(
                            action=LinePostbackAction(label="COMPLETED!", data="action=strike_boss&dmg=50")
                        )
                    ])
                )
                intent_tool = "attack"
            else:
                # 3. AI-Native Router (Phase 4)
                # Replaces manual if/else blocks for status/inventory etc.
                from app.services.ai_service import ai_router
                
                router_result = await ai_router.router(session, user_id, user_text)
                if isinstance(router_result, tuple) and len(router_result) == 3:
                    response_message, intent_tool, result_data = router_result
                else:
                    response_message, intent_tool = router_result
            
            # Persona Logic (Simplified for now, Router returns message directly)
            if intent_tool in ["get_status", "get_inventory", "get_quests"]:
                sender_persona = persona_service.SYSTEM
            elif intent_tool in ["set_goal", "use_item"]:
                sender_persona = persona_service.MENTOR
            else:
                sender_persona = persona_service.SYSTEM

            # 4. Prepend Rival Narrative if exists
            if rival_log:
                if isinstance(response_message, TextMessage):
                    response_message.text = f"{rival_log}\n\n{response_message.text}"
                else:
                    # If it's not a TextMessage (e.g., FlexMessage), send rival_log as a separate message
                    # This case is handled below in messages_to_send construction
                    pass
            
    except Exception as e:
        logger.error(f"Error processing action: {e}", exc_info=True)
        response_message = TextMessage(text="⚠️ System Glitch: Action not logged. Check logs.")

    # Attach Sender
    response_message.sender = persona_service.get_sender_object(sender_persona)

    # Audio Fanfare (Level Up) & Reply Preparation
    messages_to_send = []
    
    # Add Rival Log if exists
    if rival_log and not isinstance(response_message, TextMessage):
         viper_msg = TextMessage(text=rival_log)
         viper_msg.sender = persona_service.get_sender_object(persona_service.VIPER)
         messages_to_send.append(viper_msg)

    messages_to_send.append(response_message)

    if result_data.get("leveled_up"):
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
    data = event.postback.data or ""
    reply_token = event.reply_token
    
    logger.info(f"Received Postback from {user_id}: {data}")

    # Parse Query String style data (e.g. action=equip&item_id=123)
    # Simple parsing:
    params = {}
    if not isinstance(data, str):
        data = str(data)
    for part in data.split('&'):
        if not isinstance(part, str) or '=' not in part:
            continue
        key, value = part.split('=', 1)
        if key:
            params[key] = value
            
    action = params.get('action')
    response_text = "Action received."
    
    try:
        async with app.core.database.AsyncSessionLocal() as session:
            messages = []
            
            if action == "reroll_quests":
                reroll_result = await quest_service.reroll_quests(session, user_id)
                if isinstance(reroll_result, tuple) and len(reroll_result) == 2:
                    quests, viper_taunt = reroll_result
                else:
                    quests, viper_taunt = reroll_result, None

                messages.append(flex_renderer.render_quest_list(quests))

                if viper_taunt:
                    messages.append(TextMessage(text=viper_taunt))

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

            elif action == "buy_item":
                item_id = params.get('item_id')
                user = await user_service.get_or_create_user(session, user_id)
                result = await shop_service.buy_item(session, user_id, item_id)
                if result["success"]:
                    messages.append(TextMessage(text=f"✅ {result['message']}"))
                else:
                    messages.append(TextMessage(text=f"❌ {result['message']}"))

            elif action == "craft":
                recipe_id = params.get('recipe_id')
                user = await user_service.get_or_create_user(session, user_id)
                result = await crafting_service.craft_item(session, user_id, recipe_id)
                if result["success"]:
                    messages.append(TextMessage(text=f"⚒️ {result['message']}"))
                else:
                     messages.append(TextMessage(text=f"❌ {result['message']}"))

            elif action == "strike_boss":
                 user = await user_service.get_or_create_user(session, user_id)
                 dmg = int(params.get('dmg', 10))
                 msg = await boss_service.deal_damage(session, user_id, dmg)
                 if msg:
                     messages.append(TextMessage(text=msg))
                 else:
                     messages.append(TextMessage(text="No active boss."))
            
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
