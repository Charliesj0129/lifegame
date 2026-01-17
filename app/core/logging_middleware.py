import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.core.context import set_request_id

logger = logging.getLogger("app.middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. Generate & Set Request ID for this context
        request_id = str(uuid.uuid4())
        set_request_id(request_id)
        
        start_time = time.time()

        # 2. Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
        except Exception as e:
            # Fatal error (Middleware caught it)
            logger.error(f"Uncaught exception in middleware: {e}", exc_info=True)
            status_code = 500
            raise e
        finally:
            # 3. Log Latency if enabled
            if settings.ENABLE_LATENCY_LOGS:
                process_time = (time.time() - start_time) * 1000
                
                # We pass a dict as 'extra' so JSONFormatter can merge it
                logger.info(
                    "Request finished",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "duration_ms": round(process_time, 2),
                        "client_ip": request.client.host if request.client else None,
                    }
                )

        return response
