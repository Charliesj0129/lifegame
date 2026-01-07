from fastapi import APIRouter, Request, Header, HTTPException
from app.schemas.game_schemas import GameResult
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

from legacy.services.line_bot import get_line_handler, get_messaging_api
from app.core.config import settings
from legacy.services.flex_renderer import flex_renderer
from legacy.services.persona_service import persona_service
from legacy.services.audio_service import audio_service
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

from legacy.services.user_service import user_service
import app.core.database
from legacy.services.quest_service import quest_service
from legacy.services.boss_service import boss_service
from legacy.services.shop_service import shop_service
from legacy.services.crafting_service import crafting_service
from legacy.services.rival_service import rival_service
from legacy.services.verification_service import verification_service
from legacy.services.lore_service import lore_service
from legacy.handlers import setup_dispatcher

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
    try:
        from application.services.game_loop import game_loop
        from domain.models.game_result import GameResult
        from adapters.perception.line_client import line_client

        async with app.core.database.AsyncSessionLocal() as session:
            # Delegate entire orchestration to GameLoop
            game_result = await game_loop.process_message(session, user_id, raw_text)

        await line_client.send_reply(reply_token, game_result)

    except Exception as e:
        logger.error(f"Handle Message Failed: {e}", exc_info=True)
        # Fallback Reply
        try:
             from adapters.perception.line_client import line_client
             from domain.models.game_result import GameResult
             err_res = GameResult(text=f"⚠️ 系統異常: {uuid.uuid4().hex[:8]}")
             await line_client.send_reply(reply_token, err_res)
        except Exception:
             logger.error("Critical Failure in Error Handler")


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
        logger.error(f"Image processing failed: {e}", exc_info=True)
        response_message = GameResult(text="⚠️ 圖片處理失敗")

    try:
        from adapters.perception.line_client import line_client
        if not isinstance(response_message, GameResult):
             # Ensure it is GameResult if logic above returned TextMessage (legacy)
             # But wait, above logic sets response_message = TextMessage(...)
             # I need to change above logic or convert here.
             # Let's convert here for safety.
             if isinstance(response_message, TextMessage):
                 response_message = GameResult(text=response_message.text)
        
        await line_client.send_reply(reply_token, response_message)
    except Exception as e:
        logger.error(f"Failed to send image reply: {e}", exc_info=True)


@webhook_handler.add(MessageEvent, message=LocationMessageContent)
async def handle_location_message(event: MessageEvent):
    user_id = event.source.user_id
    reply_token = event.reply_token
    game_result = GameResult(text="⚠️ 位置驗證失敗，請稍後再試。")

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
            game_result = GameResult(text=message)

    except Exception as e:
        # legacy error builder returns TextMessage
        # We should just log and set text
        logger.error(f"Location failed: {e}")
        game_result = GameResult(text="⚠️ 系統異常")

    try:
        from adapters.perception.line_client import line_client
        await line_client.send_reply(reply_token, game_result)
    except Exception as e:
        logger.error(f"Failed to send location reply: {e}", exc_info=True)


from linebot.v3.webhooks import PostbackEvent, FollowEvent
from legacy.services.rich_menu_service import rich_menu_service

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
                from legacy.models.quest import Quest

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
                from legacy.models.dda import HabitState, DailyOutcome
                from legacy.services.dda_service import dda_service
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
        logger.error(f"Postback failed: {e}")
        response_text = "⚠️ 操作失敗"

    try:
        from adapters.perception.line_client import line_client
        from domain.models.game_result import GameResult
        
        # Determine what to send. Logic above populates `messages` list (legacy TextMessages).
        # Wrapper: If `messages` exists, we need to convert them to GameResult? 
        # LineClient only takes ONE GameResult.
        # But `messages` might have [QuestList (Flex), Taunt (Text)].
        # GameResult is SINGLE message concept usually?
        # Or GameResult should hold multiple?
        # For now, let's just pick the first one or LAST one? Or concat text?
        # Or extend LineClient to take List.
        # Given strict Phase 1 "No big bang", maybe I should let LineClient take "raw_messages" metadata?
        # or... loop and send? No, reply token only works ONCE.
        
        # HACK: If we have multiple messages, we are in trouble with simple GameResult.
        # But LineClient._to_line_messages converts GameResult -> List[Message].
        # So we need to reverse: List[Message] -> GameResult.
        # GameResult(text=..., metadata={'extra_messages': [...]})
        # Note: LineClient doesn't support 'extra_messages' yet.
        
        # Wait, I am refactoring `legacy/webhook.py`.
        # I can just construct `GameResult` that represents the *intent*.
        # Postback logic:
        # - reroll_quests -> [Flex, Text]
        # - complete_quest -> [Text(Success + Reward)] or [Text, Text]
        # - check_habit -> [Text]
        
        # Let's simplify: Send ONE message for now if possible, or concatenate text.
        # Or, update `LineClient` to allow passing raw messages in metadata as an escape hatch.
        # I will update LineClient in a subsequent edit or assume I can do it.
        # But wait, checking LineClient code I wrote:
        # It DOES NOT handle metadata['extra_messages'].
        
        # Current priority: "Line Consistency".
        # If I break multi-message replies (e.g. Flex + Taunt), I break "Invariants".
        # So I MUST support it.
        
        # Real Solution: update LineClient to support `metadata={"raw_messages": [...]}`
        # And if present, use them.
        
        game_result = GameResult(text=response_text)
        if 'messages' in locals() and messages:
            # Pass the legacy messages through metadata
            game_result.metadata = {"legacy_messages": messages}
        
        await line_client.send_reply(reply_token, game_result)
        
    except Exception as e:
        logger.error(f"Failed to reply to postback: {e}")
