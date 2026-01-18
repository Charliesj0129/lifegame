from fastapi import APIRouter, HTTPException, Depends, Header, Request
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from adapters.perception.ha_adapter import ha_adapter
from app.core.container import container
# from application.services.graph_service import graph_service
from application.services.perception_service import perception_service
from logging import getLogger

logger = getLogger(__name__)
router = APIRouter()


from typing import List
from pydantic import BaseModel, Field


# --- Response Models ---
class NPCPublicResponse(BaseModel):
    name: str
    role: str
    mood: str
    # Exclude internal_id, memory_pointers, etc.


async def verify_token(x_lifegame_token: str = Header(...)):
    if not ha_adapter.validate_token(x_lifegame_token):
        logger.warning(f"Invalid Token Attempt: {x_lifegame_token}")
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


@router.post("/nerves/perceive")
async def perceive_event(request: Request, auth: bool = Depends(verify_token), db: AsyncSession = Depends(deps.get_db)):
    """
    Home Assistant Webhook Ingress.
    Receives HA events, converts to GameEvents, and processes through perception layer.
    """
    try:
        # 2. Parse Payload
        payload = await request.json()

        # 3. Adapt to GameEvent
        game_event = ha_adapter.to_game_event(payload)

        # 4. Resolve User
        user_id = payload.get("user_id", "U_DEFAULT_CHARLIE")

        # 5. Record event to Graph Memory
        try:
            await container.graph_service.record_event(
                user_id=user_id,
                event_type=game_event.type,
                metadata={
                    "source": game_event.source,
                    "source_id": game_event.source_id,
                    "impact": ha_adapter.get_event_impact(payload.get("event_type", "manual_trigger")),
                },
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
                npc_ctx = await container.graph_service.get_npc_context(npc_name)
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


@router.get("/nerves/npcs", response_model=List[NPCPublicResponse], dependencies=[Depends(verify_token)])
async def list_npcs():
    """List all available NPCs (Public Safe Data)"""
    try:
        npcs = await container.graph_service.get_all_npcs()
        # Filter fields manually or let Pydantic do it
        return npcs
    except Exception as e:
        logger.error(f"Failed to list NPCs: {e}")
        return []


@router.get("/nerves/history/{user_id}", dependencies=[Depends(verify_token)])
async def get_user_history(user_id: str, limit: int = 10):
    """Get recent event history for a user from graph memory"""
    try:
        events = await container.graph_service.get_user_history(user_id, limit)
        return {"user_id": user_id, "events": events}
    except Exception as e:
        logger.error(f"Failed to get user history: {e}")
        return {"user_id": user_id, "events": [], "error": str(e)}
