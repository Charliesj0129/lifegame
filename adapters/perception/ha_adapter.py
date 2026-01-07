import logging
from typing import Dict, Any, Optional
from domain.events.game_event import GameEvent
from app.core.config import settings

logger = logging.getLogger(__name__)

class HaAdapter:
    """
    Adapter for Home Assistant Webhooks.
    Converts raw JSON payloads from HA into Domain GameEvents.
    """
    
    def validate_token(self, token: str) -> bool:
        # Simple Shared Secret Auth
        expected = settings.HA_WEBHOOK_SECRET
        if not expected:
            # Dangerous default, but useful for dev if not set
            return True 
        return token == expected

    def to_game_event(self, payload: Dict[str, Any]) -> GameEvent:
        """
        Convert HA Payload to GameEvent.
        Expected Payload: { "trigger": "screen_on", "entity_id": "...", "state": "on", ... }
        """
        # Support both Pydantic model (via .dict()) or raw dict
        if hasattr(payload, "dict"):
            d = payload.dict()
        else:
            d = payload

        trigger = d.get("trigger", "manual_trigger")
        entity_id = d.get("entity_id", "unknown_device")
        
        # Mapping Logic
        # We can enable complex mapping later. For now, 1:1.
        event_type = f"HA_{trigger.upper()}"
        
        return GameEvent(
            source="home_assistant",
            source_id=entity_id,
            type=event_type,
            text=f"Home Assistant Event: {trigger}",
            metadata=d
        )

# Alias for legacy compatibility
HomeAssistantAdapter = HaAdapter
# Global instance
ha_adapter = HaAdapter()
