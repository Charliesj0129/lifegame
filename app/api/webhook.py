from fastapi import APIRouter, Request, Header, HTTPException
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ReplyMessageRequest,
    TextMessage,
    ShowLoadingAnimationRequest,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent,
    LocationMessageContent,
)

from app.services.line_bot import get_line_handler, get_messaging_api
from app.core.config import settings
from app.services.flex_renderer import flex_renderer
from app.services.persona_service import persona_service
from app.services.audio_service import audio_service
import logging
import uuid

router = APIRouter()
logger = logging.getLogger("lifgame")


def _build_error_message(context: str, exc: Exception) -> TextMessage:
    error_hash = uuid.uuid4().hex[:8]
    logger.error("error_hash=%s context=%s", error_hash, context, exc_info=True)
    return TextMessage(text=f"⚠️ 系統異常，請稍後再試\n代碼：{error_hash}")


@router.post("/callback")
async def callback(request: Request, x_line_signature: str = Header(None)):
    if x_line_signature is None:
        raise HTTPException(status_code=400, detail="Missing X-Line-Signature header")

    body = await request.body()
    body_str = body.decode("utf-8")

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
from app.services.verification_service import verification_service
from app.services.lore_service import lore_service
from app.api.handlers import setup_dispatcher

# Initialize Dispatcher Strategies
setup_dispatcher()

# ... (Previous imports)


@webhook_handler.add(MessageEvent, message=TextMessageContent)
async def handle_message(event: MessageEvent):
    user_text = event.message.text
    raw_text = user_text.strip()
    raw_text.lower()
    user_id = event.source.user_id
    reply_token = event.reply_token

    # 1. Trigger Loading Animation (optional)
    if settings.ENABLE_LOADING_ANIMATION:
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
    response_message = TextMessage(text="⚠️ 系統異常")
    sender_persona = persona_service.SYSTEM
    rival_log = ""
    result_data = {}

    try:
        async with app.core.database.AsyncSessionLocal() as session:
            # 1. Get User (Required for Rival Check)
            user = await user_service.get_or_create_user(session, user_id)

            from app.services.hp_service import hp_service

            if user.is_hollowed or getattr(user, "hp_status", "") == "HOLLOWED":
                rescue_msg = await hp_service.trigger_rescue_protocol(session, user)
                response_message = TextMessage(text=f"⚠️ 瀕死狀態啟動。\n{rescue_msg}")
                sender_persona = persona_service.SYSTEM
                rival_log = ""
                intent_tool = "hollowed_rescue"
                result_data = {}
            else:
                # 2. Nemesis System: Check Inactivity & Penalties
                try:
                    rival_log = await rival_service.process_encounter(session, user)
                except Exception as e:
                    logger.warning(f"Rival encounter failed: {e}")
                    rival_log = ""

                # Dispatcher (Command Bus)
                from app.core.dispatcher import dispatcher

                response_message, intent_tool, result_data = await dispatcher.dispatch(
                    session, user_id, user_text
                )

            # Persona Logic (Simplified for now, Router returns message directly)
            if intent_tool == "hollowed_rescue":
                sender_persona = persona_service.SYSTEM
            elif intent_tool == "get_status":
                # Feature 5: Lore Progress
                lore_prog = await lore_service.get_user_progress(session, user_id)
                response_message = flex_renderer.render_status(user, lore_prog)
                sender_persona = persona_service.SYSTEM

            elif intent_tool == "get_quests":
                # Feature 6: Habits
                quests = await quest_service.get_daily_quests(session, user_id)
                habits = await quest_service.get_daily_habits(session, user_id)
                response_message = flex_renderer.render_quest_list(quests, habits)
                sender_persona = persona_service.SYSTEM

            elif intent_tool == "get_inventory":
                # (Keep existing if any, or just system persona)
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
        response_message = _build_error_message("handle_message", e)

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
                ReplyMessageRequest(reply_token=reply_token, messages=messages_to_send)
            )
            logger.info("Reply sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send reply: {e}", exc_info=True)
        # We don't raise here, so Line gets 200 OK and doesn't retry endlessly if it's a logic error.
        # But if it's a token expiry, we can't do much.


@webhook_handler.add(MessageEvent, message=ImageMessageContent)
async def handle_image_message(event: MessageEvent):
    user_id = event.source.user_id
    reply_token = event.reply_token
    response_message = TextMessage(text="⚠️ 圖片處理失敗，請稍後再試。")

    try:
        api = get_messaging_api()
        image_bytes = None
        if api:
            content = await api.get_message_content(event.message.id)
            if hasattr(content, "read"):
                image_bytes = await content.read()
            elif hasattr(content, "data"):
                image_bytes = content.data
            elif hasattr(content, "body"):
                image_bytes = content.body
            elif hasattr(content, "content"):
                image_bytes = content.content

        async with app.core.database.AsyncSessionLocal() as session:
            if image_bytes:
                result = await verification_service.process_verification(
                    session, user_id, image_bytes, "IMAGE"
                )
                message = result["message"]
                if result.get("hint"):
                    message = f"{message}\n{result['hint']}"
                response_message = TextMessage(text=message)
            else:
                response_message = TextMessage(text="⚠️ 無法讀取圖片內容，請再試一次。")

    except Exception as e:
        response_message = _build_error_message("handle_image_message", e)

    try:
        api = get_messaging_api()
        if api:
            await api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token, messages=[response_message]
                )
            )
    except Exception as e:
        logger.error(f"Failed to send image reply: {e}", exc_info=True)


@webhook_handler.add(MessageEvent, message=LocationMessageContent)
async def handle_location_message(event: MessageEvent):
    user_id = event.source.user_id
    reply_token = event.reply_token
    response_message = TextMessage(text="⚠️ 位置驗證失敗，請稍後再試。")

    try:
        lat = event.message.latitude
        lng = event.message.longitude

        async with app.core.database.AsyncSessionLocal() as session:
            result = await verification_service.process_verification(
                session, user_id, (lat, lng), "LOCATION"
            )
            message = result["message"]
            if result.get("hint"):
                message = f"{message}\n{result['hint']}"
            response_message = TextMessage(text=message)

    except Exception as e:
        response_message = _build_error_message("handle_location_message", e)

    try:
        api = get_messaging_api()
        if api:
            await api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token, messages=[response_message]
                )
            )
    except Exception as e:
        logger.error(f"Failed to send location reply: {e}", exc_info=True)


from linebot.v3.webhooks import PostbackEvent, FollowEvent
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
    for part in data.split("&"):
        if not isinstance(part, str) or "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key:
            params[key] = value

    action = params.get("action")
    response_text = "已收到操作。"

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

                response_text = "任務已重新生成。"  # Fallback log

            elif action == "complete_quest":
                quest_id = params.get("quest_id")
                user = await user_service.get_or_create_user(session, user_id)

                # Fetch Quest first
                from app.models.quest import Quest

                quest = await session.get(Quest, quest_id)

                if quest:
                    # Feature 4: Use Verification Service for Epic Feedback
                    completion = await verification_service._complete_quest(
                        session, user_id, quest
                    )
                    if completion.get("success") is False:
                        messages.append(
                            TextMessage(
                                text=completion.get("message", "⚠️ 任務已完成或不存在。")
                            )
                        )
                    else:
                        message = (
                            f"{completion.get('message', '✅ 任務完成！')}\n"
                            f"獲得：{completion.get('xp', 0)} XP / {completion.get('gold', 0)} Gold"
                        )
                        if completion.get("story"):
                            message = f"{message}\n\n_{completion['story']}_"
                        messages.append(TextMessage(text=message))
                else:
                    messages.append(TextMessage(text="⚠️ 找不到任務或已完成。"))

            elif action == "check_habit":
                habit_id = params.get("habit_id")
                # Feature 3/6: Habit Check-in
                from app.models.dda import HabitState, DailyOutcome
                from app.services.dda_service import dda_service
                from sqlalchemy import select
                import datetime

                habit = await session.get(HabitState, habit_id)
                if habit:
                    habit_tag = habit.habit_tag or habit.habit_name or habit.id
                    if not habit.habit_tag:
                        habit.habit_tag = habit_tag

                    today = datetime.date.today()
                    outcome_stmt = select(DailyOutcome).where(
                        DailyOutcome.user_id == user_id,
                        DailyOutcome.habit_tag == habit_tag,
                        DailyOutcome.date == today,
                        DailyOutcome.is_global.is_(False),
                    )
                    outcome = (await session.execute(outcome_stmt)).scalars().first()
                    if outcome and outcome.done:
                        messages.append(
                            TextMessage(
                                text=f"✅ 今日已打卡：{habit.habit_name or habit_tag}"
                            )
                        )
                    else:
                        await dda_service.record_completion(
                            session,
                            user_id,
                            habit_tag,
                            habit.tier or "T1",
                            source="check_in",
                            duration_minutes=None,
                            quest_id=None,
                        )
                        habit.exp = (habit.exp or 0) + 10
                        user = await user_service.get_or_create_user(session, user_id)
                        user.xp = (user.xp or 0) + 5  # Small reward

                        await session.commit()
                        messages.append(
                            TextMessage(
                                text=f"🔄 已打卡：{habit.habit_name or habit_tag}\n連續：{habit.zone_streak_days or 0} 天（+5 經驗）"
                            )
                        )
                else:
                    messages.append(TextMessage(text="⚠️ 找不到習慣模組。"))

            elif action == "accept_all_quests":
                response_text = "✅ 已接受全部任務！（待實作）"
                messages.append(TextMessage(text=response_text))

            elif action == "skip_rival_update":
                response_text = "⏭️ 已略過 Viper 更新。"
                messages.append(TextMessage(text=response_text))

            elif action == "equip":
                item_id = params.get("item_id")
                response_text = f"⚔️ 裝備中：{item_id}..."
                messages.append(TextMessage(text=response_text))

            elif action == "buy_item":
                item_id = params.get("item_id")
                user = await user_service.get_or_create_user(session, user_id)
                result = await shop_service.buy_item(session, user_id, item_id)
                if result["success"]:
                    messages.append(TextMessage(text=f"✅ {result['message']}"))
                else:
                    messages.append(TextMessage(text=f"❌ {result['message']}"))

            elif action == "craft":
                recipe_id = params.get("recipe_id")
                user = await user_service.get_or_create_user(session, user_id)
                result = await crafting_service.craft_item(session, user_id, recipe_id)
                if result["success"]:
                    messages.append(TextMessage(text=f"⚒️ {result['message']}"))
                else:
                    messages.append(TextMessage(text=f"❌ {result['message']}"))

            elif action == "strike_boss":
                user = await user_service.get_or_create_user(session, user_id)
                dmg = int(params.get("dmg", 10))
                msg = await boss_service.deal_damage(session, user_id, dmg)
                if msg:
                    messages.append(TextMessage(text=msg))
                else:
                    messages.append(TextMessage(text="目前沒有首領。"))

            else:
                response_text = f"未知操作：{action}"
                messages.append(TextMessage(text=response_text))

    except Exception as e:
        response_text = _build_error_message("handle_postback", e).text

    # "Silent" Reply logic?
    # Line requires a 200 OK and ideally a reply token usage or it might retry?
    # Actually we MUST reply or the user sees nothing (loading spinner stops eventually but it's bad UX).
    # We reply with a ephemeral TextMessage or a Flex update.

    try:
        api = get_messaging_api()
        if api and "messages" in locals() and messages:
            await api.reply_message(
                ReplyMessageRequest(reply_token=reply_token, messages=messages)
            )
        elif api:
            await api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token, messages=[TextMessage(text=response_text)]
                )
            )
    except Exception as e:
        logger.error(f"Failed to reply to postback: {e}")
