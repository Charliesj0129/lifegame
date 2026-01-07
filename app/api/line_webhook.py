"""
LINE Webhook Router - New Architecture
Handles LINE events and routes them through GameLoop
"""
from fastapi import APIRouter, Request, Header, HTTPException
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ShowLoadingAnimationRequest
from linebot.v3.webhooks import MessageEvent, PostbackEvent, FollowEvent, TextMessageContent, ImageMessageContent, LocationMessageContent
import logging
import uuid

from app.core.config import settings
from legacy.services.line_bot import get_messaging_api, get_line_handler
import app.core.database

router = APIRouter(prefix="/line", tags=["LINE Webhook"])
logger = logging.getLogger("lifgame.line")


@router.post("/callback")
async def line_callback(request: Request, x_line_signature: str = Header(None)):
    """
    LINE Webhook Endpoint.
    Validates signature and dispatches events to handlers.
    """
    body = await request.body()
    body_str = body.decode("utf-8")
    
    handler = get_line_handler()
    if not handler:
        raise HTTPException(status_code=500, detail="Webhook handler not initialized")
    
    try:
        await handler.handle(body_str, x_line_signature)
    except InvalidSignatureError:
        logger.warning("Invalid LINE signature received")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Webhook handling failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error")
    
    return {"status": "ok"}


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
            
            await line_client.send_reply(reply_token, game_result)
            
        except Exception as e:
            logger.error(f"Message handling failed: {e}", exc_info=True)
            await _send_error_reply(reply_token)


    @webhook_handler.add(MessageEvent, message=ImageMessageContent)
    async def handle_image_message(event: MessageEvent):
        """Handle image messages (verification photos)"""
        user_id = event.source.user_id
        reply_token = event.reply_token
        message_id = event.message.id
        
        try:
            from legacy.services.verification_service import verification_service, Verdict
            from adapters.perception.line_client import line_client
            from domain.models.game_result import GameResult
            
            async with app.core.database.AsyncSessionLocal() as session:
                verdict: Verdict = await verification_service.verify_completion(
                    session, user_id, message_id
                )
                
                result = GameResult(
                    text=verdict.narrative,
                    metadata={
                        "verified": verdict.verified,
                        "quest_id": verdict.quest_id
                    }
                )
                await line_client.send_reply(reply_token, result)
                
        except Exception as e:
            logger.error(f"Image handling failed: {e}", exc_info=True)
            await _send_error_reply(reply_token)


    @webhook_handler.add(PostbackEvent)
    async def handle_postback(event: PostbackEvent):
        """Handle postback actions from Flex Messages"""
        user_id = event.source.user_id
        reply_token = event.reply_token
        data = event.postback.data
        
        try:
            from legacy.handlers import handle_postback_data
            from adapters.perception.line_client import line_client
            from domain.models.game_result import GameResult
            
            async with app.core.database.AsyncSessionLocal() as session:
                result = await handle_postback_data(session, user_id, data)
                
                if isinstance(result, GameResult):
                    await line_client.send_reply(reply_token, result)
                elif result:
                    # Legacy tuple format (msg, tool, data)
                    game_result = GameResult(
                        text=str(result[0]) if result else "OK",
                        metadata=result[2] if len(result) > 2 else {}
                    )
                    await line_client.send_reply(reply_token, game_result)
                    
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
            from adapters.perception.line_client import line_client
            from domain.models.game_result import GameResult
            
            async with app.core.database.AsyncSessionLocal() as session:
                # Setup rich menu for new user
                await rich_menu_service.setup_rich_menu()
                
                # Welcome message
                result = GameResult(
                    text="🎮 歡迎來到 LifeOS！\n\n點擊下方選單開始你的冒險。"
                )
                await line_client.send_reply(reply_token, result)
                
        except Exception as e:
            logger.error(f"Follow handling failed: {e}", exc_info=True)


async def _send_error_reply(reply_token: str):
    """Send error message to user"""
    try:
        from adapters.perception.line_client import line_client
        from domain.models.game_result import GameResult
        
        error_hash = uuid.uuid4().hex[:8]
        result = GameResult(text=f"⚠️ 系統異常 ({error_hash})")
        await line_client.send_reply(reply_token, result)
    except Exception:
        logger.error("Critical: Failed to send error reply")
