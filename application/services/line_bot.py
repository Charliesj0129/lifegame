from linebot.v3.messaging import AsyncMessagingApi, AsyncApiClient, Configuration
from linebot.v3.webhook import WebhookHandler, WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from typing import Any
from app.core.config import settings
import logging
import inspect


class AsyncWebhookHandler(WebhookHandler):
    def __init__(self, channel_secret: str):
        super().__init__(channel_secret)
        self.parser = WebhookParser(channel_secret)

    async def handle(self, body: str, signature: str):
        if not self.parser.signature_validator.validate(body, signature):
            raise InvalidSignatureError

        events = self.parser.parse(body, signature)
        for event in events:
            await self.__invoke_async_func(event)

    async def __invoke_async_func(self, event: Any):
        # Access private method of parent class (name mangling)
        # Verify if event has message attribute to pass as payload type?
        # get_handler_key(event, payload)
        # For MessageEvent, payload is event.message?
        # Let's inspect signature of __get_handler_key. It takes (event_type, message_type).

        payload = getattr(event, "message", None)
        payload_type = type(payload) if payload else None

        key = self._WebhookHandler__get_handler_key(type(event), payload_type)
        func = self._handlers.get(key, None)
        if func is None:
            return

        if inspect.iscoroutinefunction(func):
            await func(event)
        else:
            func(event)


# Global instances
handler = None
messaging_api = None
logger = logging.getLogger(__name__)


def get_line_handler() -> AsyncWebhookHandler:
    global handler
    if handler is None:
        if settings.LINE_CHANNEL_SECRET is None:
            # In dev/test, might be None.
            logger.warning("LINE_CHANNEL_SECRET is not set. Webhooks will fail.")
            return AsyncWebhookHandler("dummy_secret")
        handler = AsyncWebhookHandler(settings.LINE_CHANNEL_SECRET)
    return handler


def get_messaging_api() -> AsyncMessagingApi:
    global messaging_api
    if messaging_api is None:
        if settings.LINE_CHANNEL_ACCESS_TOKEN is None:
            logger.warning("LINE_CHANNEL_ACCESS_TOKEN is not set. Replies will fail.")
            configuration = Configuration(access_token="dummy")
        else:
            configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)

        async_api_client = AsyncApiClient(configuration)
        messaging_api = AsyncMessagingApi(async_api_client)
    return messaging_api
