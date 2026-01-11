import logging
from typing import Dict, Any, Optional, List
from domain.events.game_event import GameEvent
from app.core.config import settings

logger = logging.getLogger(__name__)


# Event type mappings for semantic understanding
EVENT_MAPPINGS = {
    # Screen/Phone Events
    "screen_on": {"category": "device", "impact": "neutral", "concepts": ["Action"]},
    "screen_off": {"category": "device", "impact": "positive", "concepts": ["Discipline"]},
    "doomscrolling": {"category": "behavior", "impact": "negative", "concepts": ["Procrastination"]},
    # Sleep Events
    "bedtime": {"category": "health", "impact": "positive", "concepts": ["Discipline"]},
    "wake_up": {"category": "health", "impact": "positive", "concepts": ["Action"]},
    "late_night": {"category": "health", "impact": "negative", "concepts": ["Procrastination"]},
    # Exercise Events
    "workout_start": {"category": "health", "impact": "positive", "concepts": ["Exercise", "Action"]},
    "workout_end": {"category": "health", "impact": "positive", "concepts": ["Exercise", "Discipline"]},
    "steps_goal": {"category": "health", "impact": "positive", "concepts": ["Exercise"]},
    # Location Events
    "arrive_home": {"category": "location", "impact": "neutral", "concepts": []},
    "leave_home": {"category": "location", "impact": "neutral", "concepts": ["Action"]},
    "arrive_gym": {"category": "location", "impact": "positive", "concepts": ["Exercise"]},
    # Work Events
    "focus_mode_on": {"category": "productivity", "impact": "positive", "concepts": ["Discipline", "Strategy"]},
    "focus_mode_off": {"category": "productivity", "impact": "neutral", "concepts": []},
    # Default
    "manual_trigger": {"category": "manual", "impact": "neutral", "concepts": []},
}


class HaAdapter:
    """
    Adapter for Home Assistant Webhooks.
    Converts raw JSON payloads from HA into Domain GameEvents.
    """

    def validate_token(self, token: str) -> bool:
        """Validate webhook authentication token"""
        expected = settings.HA_WEBHOOK_SECRET
        if not expected:
            # Dangerous default, but useful for dev if not set
            logger.warning("HA_WEBHOOK_SECRET not set - accepting all tokens")
            return True
        return token == expected

    def to_game_event(self, payload: Dict[str, Any]) -> GameEvent:
        """
        Convert HA Payload to GameEvent with rich metadata.
        Expected Payload: { "event_type": "screen_on", "entity_id": "...", "state": "...", ... }
        """
        # Support both Pydantic model (via .dict()) or raw dict
        if hasattr(payload, "dict"):
            d = payload.dict()
        else:
            d = payload

        # Extract core fields
        event_type = d.get("event_type", d.get("trigger", "manual_trigger"))
        entity_id = d.get("entity_id", "unknown_device")
        state = d.get("state", "")

        # Get event mapping for semantic understanding
        mapping = EVENT_MAPPINGS.get(event_type, EVENT_MAPPINGS["manual_trigger"])

        # Build enriched metadata
        metadata = {
            **d,
            "category": mapping["category"],
            "impact": mapping["impact"],
            "related_concepts": mapping["concepts"],
        }

        # Generate human-readable text based on event type
        text = self._generate_event_text(event_type, entity_id, state, d)

        return GameEvent(
            source="home_assistant", source_id=entity_id, type=f"HA_{event_type.upper()}", text=text, metadata=metadata
        )

    def _generate_event_text(self, event_type: str, entity_id: str, state: str, data: Dict) -> str:
        """Generate human-readable event description for narrative generation"""
        templates = {
            "screen_on": "使用者打開了手機螢幕",
            "screen_off": "使用者關閉了手機螢幕，可能正在專注",
            "doomscrolling": "使用者在深夜仍在滑手機（可能在刷社交媒體）",
            "bedtime": "使用者準備就寢",
            "wake_up": "使用者醒來開始新的一天",
            "late_night": "深夜了，使用者還沒睡覺",
            "workout_start": "使用者開始運動了！",
            "workout_end": "使用者完成了運動，做得好！",
            "steps_goal": "使用者達成了今日步數目標",
            "arrive_home": "使用者到家了",
            "leave_home": "使用者離開家了",
            "arrive_gym": "使用者到達健身房",
            "focus_mode_on": "使用者開啟了專注模式",
            "focus_mode_off": "使用者關閉了專注模式",
        }

        base_text = templates.get(event_type, f"Home Assistant 事件: {event_type}")

        # Add context from attributes if available
        attributes = data.get("attributes", {})
        if attributes:
            if "battery" in attributes:
                base_text += f"（電量 {attributes['battery']}%）"
            if "duration" in attributes and attributes["duration"] != "unknown":
                base_text += f"（持續 {attributes['duration']}）"

        return base_text

    def get_interested_npcs(self, event_type: str) -> List[str]:
        """
        Determine which NPCs should react to this event based on their preferences.
        Returns list of NPC names who care about the related concepts.
        """
        mapping = EVENT_MAPPINGS.get(event_type, EVENT_MAPPINGS["manual_trigger"])
        concepts = mapping.get("concepts", [])

        # NPC interest mapping (could be queried from graph in future)
        npc_interests = {
            "Viper": ["Discipline", "Exercise", "Procrastination"],
            "Sage": ["Learning", "Meditation", "Strategy"],
            "Ember": ["Action", "Exercise"],
            "Shadow": ["Strategy"],
        }

        interested = []
        for npc, interests in npc_interests.items():
            if any(concept in interests for concept in concepts):
                interested.append(npc)

        # Default to Viper if no specific NPC cares
        if not interested:
            interested = ["Viper"]

        return interested

    def get_event_impact(self, event_type: str) -> str:
        """Get the impact type for an event (positive/negative/neutral)"""
        mapping = EVENT_MAPPINGS.get(event_type, EVENT_MAPPINGS["manual_trigger"])
        return mapping.get("impact", "neutral")


# Alias for legacy compatibility
HomeAssistantAdapter = HaAdapter
# Global instance
ha_adapter = HaAdapter()
