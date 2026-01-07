from fastapi import APIRouter, HTTPException, Depends, Header, Request
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from adapters.perception.ha_adapter import ha_adapter
from application.services.game_loop import game_loop
from logging import getLogger

logger = getLogger(__name__)
router = APIRouter()

@router.post("/nerves/perceive")
async def perceive_event(
    request: Request,
    x_lifegame_token: str = Header(None),
    db: AsyncSession = Depends(deps.get_db)
):
    """
    Home Assistant Webhook Ingress.
    """
    # 1. Auth
    if not ha_adapter.validate_token(x_lifegame_token):
        logger.warning(f"Invalid Token: {x_lifegame_token}")
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # 2. Parse Payload
        # We accept Dict directly (FastAPI handles JSON body if mapped, but here generic)
        payload = await request.json()
        
        # 3. Adapt
        game_event = ha_adapter.to_game_event(payload)
        
        # 4. Resolve User
        # For Phase 2 single-player, default or from payload
        user_id = payload.get("user_id", "U_DEFAULT_CHARLIE") 
        
        # 5. Process in GameLoop
        # We pass the event text. GameLoop will handle Vitals/Rival checks too!
        result = await game_loop.process_message(db, user_id, game_event.text)
        
        return {
            "status": "processed",
            "narrative": result.text,
            "actions": result.metadata.get("actions", []),
            "event_id": game_event.id
        }

    except Exception as e:
        logger.error(f"Perception Error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
