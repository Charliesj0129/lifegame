from contextvars import ContextVar
from typing import Optional
import uuid

# Global context variable for Request ID
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

def get_request_id() -> str:
    return request_id_ctx.get() or "n/a"

def set_request_id(request_id: str):
    request_id_ctx.set(request_id)
