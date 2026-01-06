import time
import json
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings

# Configure json logger if needed, but for now we'll just format manually or use structlog later.
# We'll use standard logging but format the message as JSON if enabled.

logger = logging.getLogger("app.middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.ENABLE_LATENCY_LOGS:
            return await call_next(request)

        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise e
        finally:
            process_time = (time.time() - start_time) * 1000

            log_data = {
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(process_time, 2),
                "client_ip": request.client.host if request.client else None,
            }

            # If we want pure JSON logs, we should configure the formatter.
            # For now, we log as info with dict which can be parsed.
            logger.info(json.dumps(log_data))

        return response
