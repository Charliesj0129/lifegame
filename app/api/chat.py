from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from application.services.social_service import social_service

# We might need auth dependency later, but for now open or consistent with Line Webhook logic?
# Actually, if this is called by frontend or Line Webhook, it's internal.
# But if it's a REST API for a future frontend, it needs Auth.
# Leaning towards simple API first.

router = APIRouter(prefix="/chat", tags=["Social"])


class ChatRequest(BaseModel):
    user_id: str
    text: str


class ChatResponse(BaseModel):
    text: str
    can_visualize: bool = False
    metadata: Optional[Dict[str, Any]] = None


@router.post("/{npc_id}", response_model=ChatResponse)
async def chat_with_npc(npc_id: str, request: ChatRequest):
    """
    Interact with an NPC.
    """
    try:
        response = await social_service.interact(request.user_id, npc_id, request.text)
        return ChatResponse(
            text=response["text"], can_visualize=response.get("can_visualize", False), metadata=response
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
