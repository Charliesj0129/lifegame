from fastapi import APIRouter, Request, Header, HTTPException
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import AsyncApiClient, AsyncMessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from app.services.line_bot import get_line_handler, get_messaging_api
from app.services.ai_engine import ai_engine
from app.services.flex_renderer import flex_renderer
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

@webhook_handler.add(MessageEvent, message=TextMessageContent)
async def handle_message(event: MessageEvent):
    user_text = event.message.text
    user_id = event.source.user_id
    reply_token = event.reply_token

    logger.info(f"Received message from {user_id}: {user_text}")

    # Execute Logic
    response_message = TextMessage(text="System Error")
    try:
        async with app.core.database.AsyncSessionLocal() as session:
            # Command Handling
            if user_text.strip().lower() == "status":
                user = await user_service.get_or_create_user(session, user_id)
                response_message = flex_renderer.render_status(user)
            elif user_text.strip().lower() == "inventory":
                items = await inventory_service.get_user_inventory(session, user_id)
                if not items:
                    response_message = TextMessage(text="🎒 Inventory is empty.")
                else:
                    item_list = "\n".join([f"- {ui.item.name} x{ui.quantity}" for ui in items])
                    response_message = TextMessage(text=f"🎒 **INVENTORY** 🎒\n{item_list}")
            
            elif user_text.strip().lower().startswith("use "):
                item_keyword = user_text.strip()[4:]
                result_text = await inventory_service.use_item(session, user_id, item_keyword)
                response_message = TextMessage(text=result_text)
            else:
                # Regular Action
                result = await user_service.process_action(session, user_id, user_text)
                response_message = flex_renderer.render(result)
            
    except Exception as e:
        logger.error(f"Error processing action: {e}", exc_info=True)
        response_message = TextMessage(text="⚠️ System Glitch: Action not logged. Check logs.")

    # Reply
    # Reply
    try:
        api = get_messaging_api()
        if api:
            logger.info(f"Attempting to reply with token: {reply_token}...")
            await api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[response_message]
                )
            )
            logger.info("Reply sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send reply: {e}", exc_info=True)
        # We don't raise here, so Line gets 200 OK and doesn't retry endlessly if it's a logic error.
        # But if it's a token expiry, we can't do much.


