from fastapi import APIRouter, HTTPException, Depends, Header, Request
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from adapters.perception.ha_adapter import ha_adapter
from app.services.graph_service import graph_service
from app.services.perception_service import perception_service
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
    Receives HA events, converts to GameEvents, and processes through perception layer.
    """
    # 1. Auth
    if not ha_adapter.validate_token(x_lifegame_token):
        logger.warning(f"Invalid Token: {x_lifegame_token}")
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # 2. Parse Payload
        payload = await request.json()
        
        # 3. Adapt to GameEvent
        game_event = ha_adapter.to_game_event(payload)
        
        # 4. Resolve User
        user_id = payload.get("user_id", "U_DEFAULT_CHARLIE")
        
        # 5. Record event to Graph Memory
        try:
            graph_service.record_event(
                user_id=user_id,
                event_type=game_event.type,
                metadata={
                    "source": game_event.source,
                    "source_id": game_event.source_id,
                    "impact": ha_adapter.get_event_impact(payload.get("event_type", "manual_trigger")),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to record event to graph: {e}")
        
        # 6. Get interested NPCs for this event
        event_type = payload.get("event_type", payload.get("trigger", "manual_trigger"))
        interested_npcs = ha_adapter.get_interested_npcs(event_type)
        
        # 7. Process through PerceptionService with NPC context
        result = await perception_service.process_event(game_event, db)
        
        # 8. Enrich response with NPC info
        npc_contexts = []
        for npc_name in interested_npcs[:2]:  # Limit to 2 NPCs
            try:
                npc_ctx = graph_service.get_npc_context(npc_name)
                npc_contexts.append(npc_ctx)
            except Exception:
                pass
        
        return {
            "status": "processed",
            "narrative": result.text,
            "actions": result.metadata.get("actions_taken", []),
            "event_id": game_event.id,
            "interested_npcs": [npc["name"] for npc in npc_contexts],
            "impact": ha_adapter.get_event_impact(event_type),
        }

    except Exception as e:
        logger.error(f"Perception Error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@router.get("/nerves/npcs")
async def list_npcs():
    """List all available NPCs and their personalities"""
    try:
        npcs = graph_service.get_all_npcs()
        return {"npcs": npcs}
    except Exception as e:
        logger.error(f"Failed to list NPCs: {e}")
        return {"npcs": [], "error": str(e)}


@router.get("/nerves/history/{user_id}")
async def get_user_history(user_id: str, limit: int = 10):
    """Get recent event history for a user from graph memory"""
    try:
        events = graph_service.get_user_history(user_id, limit)
        return {"user_id": user_id, "events": events}
    except Exception as e:
        logger.error(f"Failed to get user history: {e}")
        return {"user_id": user_id, "events": [], "error": str(e)}

