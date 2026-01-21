"""
LINE Webhook Router - New Architecture
Handles LINE events and routes them through GameLoop
"""

import json
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ShowLoadingAnimationRequest
from linebot.v3.webhooks import (
    FollowEvent,
    ImageMessageContent,
    LocationMessageContent,
    MessageEvent,
    PostbackEvent,
    TextMessageContent,
)
from sqlalchemy.ext.asyncio import AsyncSession

import app.core.database
from app.core.config import settings
from app.core.context import get_request_id, set_request_id
from application.services.line_bot import get_line_handler, get_messaging_api

router = APIRouter(prefix="/line", tags=["LINE Webhook"])
logger = logging.getLogger("lifgame.line")


async def process_webhook_background(body_str: str, signature: str, request_id: str | None = None):
    """
    Background Task: Process webhook logic safely.
    Catches all errors to ensure 'Silent Failure' does not happen.
    """
    if request_id:
        set_request_id(request_id)

    handler = get_line_handler()
    if not handler:
        logger.error("Handler not initialized in background task")
        return

    try:
        await handler.handle(body_str, signature)
    except Exception as e:
        logger.error(f"CRITICAL: Background Webhook Validation/Processing Failed: {e}", exc_info=True)

        # Attempt "Last Resort" Reply if possible
        try:
            data = json.loads(body_str)
            events = data.get("events", [])
            for event in events:
                reply_token = event.get("replyToken")
                if reply_token:
                    await _send_friendly_error_reply(reply_token, "BG_FAIL")
        except Exception as parse_err:
            logger.error(f"Double Fault: Could not parse body for error reply: {parse_err}")


async def _send_friendly_error_reply(reply_token: str, error_code: str = "UH_OH", error_detail: str = ""):
    """
    Send a friendly 'System Hiccup' Flex Message to the user.
    Includes the Request ID and optional error detail for debugging.
    """
    try:
        from adapters.perception.line_client import line_client
        from application.services.flex_renderer import flex_renderer
        from domain.models.game_result import GameResult

        req_id = get_request_id()
        # Fallback to UUID if n/a
        if not req_id or req_id == "n/a":
            req_id = uuid.uuid4().hex[:8]
        else:
            req_id = req_id[:8]

        # Include error detail if provided (for debugging)
        if error_detail:
            msg_text = f"⚠️ 系統異常 ({error_code}): {error_detail[:100]}"
        else:
            msg_text = f"🔧 系統異常 (ID: {req_id})\n守護精靈正在搶修連線... 請稍後再試。"

        result = GameResult(text=msg_text)
        await line_client.send_reply(reply_token, result)
    except Exception:
        logger.error("Critical: Failed to send error reply", exc_info=True)


@router.post("/callback")
async def line_callback(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    """
    LINE Webhook Endpoint (Async + Resilient).
    1. Validate Signature (Fast).
    2. Return 200 OK (Instant).
    3. Process Logic in Background (No Timeout).
    """
    body = await request.body()
    body_str = body.decode("utf-8")

    # Capture Request ID to pass to background task
    req_id = get_request_id()

    # 1. Validation (Fail Fast) with Debug Bypass
    x_debug_bypass = request.headers.get("X-Debug-Bypass")

    if x_debug_bypass == "true":
        logger.warning("Debug Bypass Active: Skipping Signature Validation")
    else:
        if x_line_signature is None:
            logger.warning("Missing X-Line-Signature header")
            raise HTTPException(status_code=400, detail="Missing X-Line-Signature header")

        handler = get_line_handler()
        if not handler:
            raise HTTPException(status_code=500, detail="Handler not init")

        try:
            if not handler.parser.signature_validator.validate(body_str, x_line_signature):
                raise InvalidSignatureError
        except InvalidSignatureError:
            logger.warning("Invalid LINE signature")
            raise HTTPException(status_code=400, detail="Invalid signature")

    # 2. Enqueue Background Task with Context
    background_tasks.add_task(process_webhook_background, body_str, x_line_signature, req_id)

    # 3. ACK Immediately
    return {"status": "accepted", "mode": "async_processing"}


# Event Handlers
webhook_handler = get_line_handler()

if webhook_handler:

    @webhook_handler.add(MessageEvent, message=TextMessageContent)
    async def handle_text_message(event: MessageEvent, session: AsyncSession | None = None):
        """Handle incoming text messages"""
        user_id = event.source.user_id
        user_text = event.message.text.strip()
        reply_token = event.reply_token

        # Optional: Show loading animation
        if settings.ENABLE_LOADING_ANIMATION:
            try:
                api = get_messaging_api()
                if api:
                    await api.show_loading_animation(ShowLoadingAnimationRequest(chat_id=user_id, loading_seconds=10))
            except Exception as e:
                logger.warning(f"Loading animation failed: {e}")

        # Check for Help/Manual (Legacy Intercept)
        if user_text.lower() in ["help", "manual", "menu", "幫助", "說明", "選單"]:
            try:
                from linebot.v3.messaging import FlexMessage, ReplyMessageRequest

                from app.core.container import container
                from application.services.flex_renderer import flex_renderer
                from application.services.help_service import help_service

                async with app.core.database.AsyncSessionLocal() as session:
                    # Get user context
                    user = await container.user_service.get_or_create_user(session, user_id)
                    help_data = await help_service.get_dynamic_help(session, user)
                    flex = flex_renderer.render_help_card(help_data)

                    # Direct Reply
                    api = get_messaging_api()
                    if api:
                        await api.reply_message(
                            ReplyMessageRequest(
                                reply_token=reply_token, messages=[FlexMessage(alt_text="提示", contents=flex)]
                            )
                        )
                return
            except Exception as e:
                logger.error(f"Help command failed: {e}")
                # Fallthrough to GameLoop if fail

        # Process through GameLoop
        try:
            from adapters.perception.line_client import line_client
            from application.services.game_loop import game_loop
            from domain.models.game_result import GameResult

            async with app.core.database.AsyncSessionLocal() as session:
                game_result = await game_loop.process_message(session, user_id, user_text)

            try:
                await line_client.send_reply(reply_token, game_result)
            except Exception as reply_err:
                logger.warning(f"Reply failed ({reply_err}), attempting Push to {user_id}")
                await line_client.send_push(user_id, game_result)

        except Exception as e:
            logger.error(f"Message handling failed: {e}", exc_info=True)
            await _send_friendly_error_reply(reply_token, "MSG_FAIL", str(e))

    @webhook_handler.add(MessageEvent, message=ImageMessageContent)
    async def handle_image_message(event: MessageEvent):
        """Handle image messages (verification photos)"""
        user_id = event.source.user_id
        reply_token = event.reply_token

        try:
            from adapters.perception.line_client import line_client
            from application.services.verification_service import verification_service
            from domain.models.game_result import GameResult

            # Get image content
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

            async with app.core.database.AsyncSessionLocal() as session:
                if image_bytes:
                    result = await verification_service.process_verification(session, user_id, image_bytes, "IMAGE")
                    message = result.get("message", "驗證完成")
                    if result.get("hint"):
                        message = f"{message}\n{result['hint']}"
                    game_result = GameResult(text=message)
                else:
                    game_result = GameResult(text="⚠️ 無法讀取圖片內容，請再試一次。")

                await line_client.send_reply(reply_token, game_result)

        except Exception as e:
            logger.error(f"Image handling failed: {e}", exc_info=True)
            await _send_friendly_error_reply(reply_token, "IMG_FAIL")

    @webhook_handler.add(PostbackEvent)
    async def handle_postback(event: PostbackEvent):
        """Handle postback actions from Flex Messages"""
        user_id = event.source.user_id
        reply_token = event.reply_token
        data = event.postback.data or ""

        logger.info(f"Received Postback from {user_id}: {data}")

        # Parse Query String style data (e.g. action=equip&item_id=123)
        params = {}
        if not isinstance(data, str):
            data = str(data)
        for part in data.split("&"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            if key:
                params[key] = value

        action = params.get("action")

        try:
            from adapters.perception.line_client import line_client
            from app.core.container import container
            from application.services.flex_renderer import flex_renderer
            from application.services.inventory_service import inventory_service
            from application.services.quest_service import QuestService, quest_service
            from application.services.shop_service import shop_service
            from domain.models.game_result import GameResult

            async with app.core.database.AsyncSessionLocal() as session:
                response_text = "已收到操作。"

                if action == "reroll_quests":
                    qs: QuestService = quest_service
                    reroll_result = await qs.reroll_quests(session, user_id)  # type: ignore[attr-defined]
                    if isinstance(reroll_result, tuple) and len(reroll_result) >= 2:
                        quests, viper_taunt = reroll_result[:2]
                    else:
                        quests, viper_taunt = reroll_result, None

                    if quests is None:
                        # Quests is None means Error or Insufficient funds
                        result = GameResult(text=viper_taunt or "⚠️ 無法重骰")
                    else:
                        flex_msg = flex_renderer.render_quest_list(quests)
                        result = GameResult(text=viper_taunt or "任務已重新生成！", metadata={"flex_message": flex_msg})

                elif action == "complete_quest":
                    quest_id = params.get("quest_id")
                    if quest_id:
                        complete_res = await quest_service.complete_quest(session, user_id, quest_id)
                        if complete_res:
                            # Use new LootService feedback
                            loot = complete_res["loot"]
                            flavor = loot.narrative_flavor
                            xp = loot.xp
                            msg = f"✅ 任務完成！\n獲得 {xp} XP ({flavor})"
                            result = GameResult(text=msg)
                        else:
                            result = GameResult(text="⚠️ 任務已完成或無法找到。")
                    else:
                        result = GameResult(text="⚠️ 缺少任務ID")

                elif action == "accept_all_quests":
                    qs = quest_service
                    await qs.accept_all_pending(session, user_id)
                    result = GameResult(text="已接受所有任務！")

                elif action == "craft":
                    recipe_id = params.get("recipe_id")
                    from application.services.crafting_service import crafting_service

                    if recipe_id:
                        craft_result = await crafting_service.craft_item(session, user_id, recipe_id)
                        # craft_result is {"success": bool, "message": str}
                        msg = craft_result.get("message", "合成結束")
                        result = GameResult(text=msg)
                    else:
                        result = GameResult(text="⚠️ 缺少配方ID")

                elif action == "spawn_boss":
                    from application.services.boss_service import boss_service

                    spawn_msg = await boss_service.spawn_boss(session, user_id)
                    result = GameResult(text=spawn_msg)

                elif action == "attack_boss":
                    from application.services.boss_service import boss_service

                    # Simple MVP: Deal 100 damage
                    dmg_msg = await boss_service.deal_damage(session, user_id, 100)
                    if dmg_msg:
                        result = GameResult(text=dmg_msg)
                    else:
                        result = GameResult(text="⚠️ 沒有活躍的首領")

                elif action == "profile":
                    from application.services.flex_renderer import flex_renderer

                    user = await container.user_service.get_user(session, user_id)
                    if user:
                        flex = flex_renderer.render_profile(user)
                        result = GameResult(text="用戶設定", intent="profile", metadata={"flex_message": flex})
                    else:
                        result = GameResult(text="⚠️ 找不到用戶")

                elif action == "toggle_setting":
                    key = params.get("key")
                    value_str = params.get("value")
                    # Parse value (simple bool/string)
                    final_val = value_str
                    if value_str and value_str.lower() == "true":
                        final_val = True
                    elif value_str and value_str.lower() == "false":
                        final_val = False

                    if key:
                        await container.user_service.update_setting(session, user_id, key, final_val)

                        # Re-render profile
                        from application.services.flex_renderer import flex_renderer

                        user = await container.user_service.get_user(session, user_id)
                        flex = flex_renderer.render_profile(user)
                        result = GameResult(
                            text=f"設定已更新: {key}", intent="profile", metadata={"flex_message": flex}
                        )
                    else:
                        result = GameResult(text="⚠️ 缺少設定鍵值")

                elif action == "buy_item":
                    item_id = params.get("item_id")
                    if item_id:
                        buy_result = await shop_service.buy_item(session, user_id, item_id)
                        # buy_result is {"success": bool, "message": str}
                        msg = buy_result.get("message", "交易結束")
                        result = GameResult(text=msg)
                    else:
                        result = GameResult(text="⚠️ 缺少物品ID")

                elif action == "equip":
                    item_id = params.get("item_id")
                    if item_id:
                        equip_result = await inventory_service.equip_item(session, user_id, int(item_id))
                        result = GameResult(text=equip_result)
                    else:
                        result = GameResult(text="⚠️ 缺少物品ID")

                else:
                    result = GameResult(text=response_text)

                await line_client.send_reply(reply_token, result)

        except Exception as e:
            logger.error(f"Postback handling failed: {e}", exc_info=True)
            await _send_friendly_error_reply(reply_token, "PB_FAIL")

    @webhook_handler.add(FollowEvent)
    async def handle_follow(event: FollowEvent):
        """Handle new user follows"""
        user_id = event.source.user_id
        reply_token = event.reply_token

        try:
            from adapters.perception.line_client import line_client
            from app.core.container import container
            from application.services.rich_menu_service import rich_menu_service
            from domain.models.game_result import GameResult

            async with app.core.database.AsyncSessionLocal() as session:
                # Create user if not exists
                await container.user_service.get_or_create_user(session, user_id)

            # Link user to main rich menu (sync call)
            rich_menu_service.link_user(user_id, "MAIN")

            # Welcome message
            result = GameResult(text="🎮 歡迎來到 LifeOS！\n\n點擊下方選單開始你的冒險。")
            await line_client.send_reply(reply_token, result)

        except Exception as e:
            logger.error(f"Follow handling failed: {e}", exc_info=True)
