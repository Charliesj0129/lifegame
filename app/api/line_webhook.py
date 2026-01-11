"""
LINE Webhook Router - New Architecture
Handles LINE events and routes them through GameLoop
"""
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ShowLoadingAnimationRequest
from linebot.v3.webhooks import MessageEvent, PostbackEvent, FollowEvent, TextMessageContent, ImageMessageContent, LocationMessageContent
import logging
import uuid
import json

from app.core.config import settings
from legacy.services.line_bot import get_messaging_api, get_line_handler
import app.core.database

router = APIRouter(prefix="/line", tags=["LINE Webhook"])
logger = logging.getLogger("lifgame.line")


async def process_webhook_background(body_str: str, signature: str):
    """
    Background Task: Process webhook logic safely.
    Catches all errors to ensure 'Silent Failure' does not happen.
    """
    handler = get_line_handler()
    if not handler:
        logger.error("Handler not initialized in background task")
        return

    try:
        await handler.handle(body_str, signature)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        try:
            with open("./data/current_error.png", "w") as f: # Use .png to maybe trick webssh if needed, but .log is fine
                 f.write(f"CRITICAL ERROR: {e}\n{tb}")
        except Exception:
             pass
        logger.error(f"CRITICAL: Background Webhook Validation/Processing Failed: {e}", exc_info=True)
        # Attempt "Last Resort" Reply if possible
        # We need to parse the body manually to get the replyToken if the handler crashed logic-side
        # but handled the parsing?
        # If handler.handle() raises, it means parsing failed OR event handler raised.
        # Let's try to verify if we can recover a token.
        try:
            data = json.loads(body_str)
            events = data.get("events", [])
            for event in events:
                reply_token = event.get("replyToken")
                if reply_token:
                    await _send_error_reply(reply_token, "CRITICAL_BG_FAIL")
        except Exception as parse_err:
             logger.error(f"Double Fault: Could not parse body for error reply: {parse_err}")


# ... (Handlers remain the same, just showing the end of file fix) ...

async def _send_error_reply(reply_token: str, error_code: str = "UNKNOWN"):
    """Send error message to user (Safety Net)"""
    try:
        from adapters.perception.line_client import line_client
        from domain.models.game_result import GameResult
        
        error_hash = uuid.uuid4().hex[:8]
        msg = f"🔧 系統維護中 ({error_code}-{error_hash})\n\n守護精靈正在修復連結..."
        result = GameResult(text=msg)
        await line_client.send_reply(reply_token, result)
    except Exception:
        logger.error("Critical: Failed to send error reply")


@router.post("/callback")
async def line_callback(
    request: Request, 
    background_tasks: BackgroundTasks,
    x_line_signature: str = Header(None)
):
    """
    LINE Webhook Endpoint (Async + Resilient).
    1. Validate Signature (Fast).
    2. Return 200 OK (Instant).
    3. Process Logic in Background (No Timeout).
    """
    body = await request.body()
    body_str = body.decode("utf-8")
    
    # 1. Validation (Fail Fast)
    if x_line_signature is None:
        logger.warning("Missing X-Line-Signature header")
        raise HTTPException(status_code=400, detail="Missing X-Line-Signature header")
    
    handler = get_line_handler()
    if not handler:
         raise HTTPException(status_code=500, detail="Handler not init")

    # Use parser to validate signature ONLY, without processing events yet?
    # handler.parser.signature_validator.validate(body_str, x_line_signature)
    # But AsyncWebhookHandler doesn't expose validator easily without parsing.
    # However, handler.handle() does validation.
    # We can trust handler.handle() in background, OR double check signature here.
    # Ideally check signature here to reject bad requests immediately.
    try:
        if not handler.parser.signature_validator.validate(body_str, x_line_signature):
             raise InvalidSignatureError
    except InvalidSignatureError:
        logger.warning("Invalid LINE signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 2. Enqueue Background Task
    background_tasks.add_task(process_webhook_background, body_str, x_line_signature)
    
    # 3. ACK Immediately
    return {"status": "accepted", "mode": "async_processing"}


# Event Handlers
webhook_handler = get_line_handler()

if webhook_handler:
    
    @webhook_handler.add(MessageEvent, message=TextMessageContent)
    async def handle_text_message(event: MessageEvent):
        """Handle incoming text messages"""
        user_id = event.source.user_id
        user_text = event.message.text.strip()
        reply_token = event.reply_token
        
        # Optional: Show loading animation
        if settings.ENABLE_LOADING_ANIMATION:
            try:
                api = get_messaging_api()
                if api:
                    await api.show_loading_animation(
                        ShowLoadingAnimationRequest(chat_id=user_id, loading_seconds=10)
                    )
            except Exception as e:
                logger.warning(f"Loading animation failed: {e}")
        
        # Process through GameLoop
        try:
            from application.services.game_loop import game_loop
            from adapters.perception.line_client import line_client
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
            await _send_error_reply(reply_token)


    @webhook_handler.add(MessageEvent, message=ImageMessageContent)
    async def handle_image_message(event: MessageEvent):
        """Handle image messages (verification photos)"""
        user_id = event.source.user_id
        reply_token = event.reply_token
        
        try:
            from legacy.services.verification_service import verification_service
            from adapters.perception.line_client import line_client
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
                    result = await verification_service.process_verification(
                        session, user_id, image_bytes, "IMAGE"
                    )
                    message = result.get("message", "驗證完成")
                    if result.get("hint"):
                        message = f"{message}\n{result['hint']}"
                    game_result = GameResult(text=message)
                else:
                    game_result = GameResult(text="⚠️ 無法讀取圖片內容，請再試一次。")
                    
                await line_client.send_reply(reply_token, game_result)
                
        except Exception as e:
            logger.error(f"Image handling failed: {e}", exc_info=True)
            await _send_error_reply(reply_token)


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
            from domain.models.game_result import GameResult
            from legacy.services.quest_service import quest_service
            from legacy.services.shop_service import shop_service
            from legacy.services.inventory_service import inventory_service
            from legacy.services.flex_renderer import flex_renderer
            
            async with app.core.database.AsyncSessionLocal() as session:
                response_text = "已收到操作。"
                
                if action == "reroll_quests":
                    reroll_result = await quest_service.reroll_quests(session, user_id)
                    if isinstance(reroll_result, tuple) and len(reroll_result) == 2:
                        quests, viper_taunt = reroll_result
                    else:
                        quests, viper_taunt = reroll_result, None
                    flex_msg = flex_renderer.render_quest_list(quests)
                    result = GameResult(
                        text=viper_taunt or "任務已重新生成！",
                        metadata={"flex_message": flex_msg}
                    )

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
                    await quest_service.accept_all_pending(session, user_id)
                    result = GameResult(text="✅ 已接受所有任務！")
                    
                elif action == "buy_item":
                    item_id = params.get("item_id")
                    if item_id:
                        buy_result = await shop_service.buy_item(session, user_id, item_id)
                        result = GameResult(text=buy_result)
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
            await _send_error_reply(reply_token)


    @webhook_handler.add(FollowEvent)
    async def handle_follow(event: FollowEvent):
        """Handle new user follows"""
        user_id = event.source.user_id
        reply_token = event.reply_token
        
        try:
            from legacy.services.rich_menu_service import rich_menu_service
            from legacy.services.user_service import user_service
            from adapters.perception.line_client import line_client
            from domain.models.game_result import GameResult
            
            async with app.core.database.AsyncSessionLocal() as session:
                # Create user if not exists
                await user_service.get_or_create_user(session, user_id)
            
            # Link user to main rich menu (sync call)
            rich_menu_service.link_user(user_id, "MAIN")
            
            # Welcome message
            result = GameResult(
                text="🎮 歡迎來到 LifeOS！\n\n點擊下方選單開始你的冒險。"
            )
            await line_client.send_reply(reply_token, result)
                
        except Exception as e:
            logger.error(f"Follow handling failed: {e}", exc_info=True)


async def _send_system_error_reply(reply_token: str, error_code: str = "UNKNOWN"):
    """Send error message to user (Safety Net)"""
    try:
        from adapters.perception.line_client import line_client
        from domain.models.game_result import GameResult
        
        error_hash = uuid.uuid4().hex[:8]
        msg = f"🔧 系統維護中 ({error_code}-{error_hash})\n\n守護精靈正在修復連結..."
        result = GameResult(text=msg)
        await line_client.send_reply(reply_token, result)
    except Exception:
        logger.error("Critical: Failed to send error reply")
    """Send error message to user"""
    try:
        from adapters.perception.line_client import line_client
        from domain.models.game_result import GameResult
        
        error_hash = uuid.uuid4().hex[:8]
        result = GameResult(text=f"⚠️ 系統異常 ({error_hash})")
        await line_client.send_reply(reply_token, result)
    except Exception:
        logger.error("Critical: Failed to send error reply")
