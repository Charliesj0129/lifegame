import logging
import time
from typing import Dict, Any, List, Optional
from adapters.persistence.kuzu.adapter import get_kuzu_adapter
from application.services.ai_engine import ai_engine
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class SocialService:
    """
    Handles social interactions with NPCs.
    Manages Graph Memory (Context/History) and LLM Persona generation.
    """

    def __init__(self):
        self.kuzu = get_kuzu_adapter()

    async def interact(self, user_id: str, npc_id: str, text: str) -> Dict[str, Any]:
        """
        Process a chat message from User to NPC.
        Returns: {
            "text": "Response from NPC",
            "relationship_change": 1 (intimacy change)
        }
        """
        # 1. Retrieve NPC Profile (Assume stored in Graph or Config)
        npc_profile = self._get_npc_profile(npc_id)
        if not npc_profile:
            return {"text": "那個 NPC 不存在... (Shadow Realm error)"}

        # 2. Retrieve Context (Graph)
        context = self._get_context(user_id, npc_id)

        # 3. Generate Response (AI)
        response_data = await ai_engine.generate_npc_response(persona=npc_profile, context=context, user_input=text)

        reply_text = response_data.get("text", "...")
        intimacy_delta = response_data.get("intimacy_change", 0)

        # 4. Update Graph
        await self._update_relationship(user_id, npc_id, intimacy_delta)
        self._log_interaction(user_id, npc_id, text, reply_text)

        return {"text": reply_text, "can_visualize": response_data.get("can_visualize", False)}

    def _get_npc_profile(self, npc_id: str) -> Dict[str, str]:
        # TODO: Fetch from Graph Node. For Phase 5 MVP, use hardcoded or simple query.
        profiles = {
            "viper": {
                "name": "Viper",
                "role": "Rival",
                "personality": "Competitor, Toxic User Logic, Cynical but pushing you to grow.",
            },
            "mentor": {"name": "Zenith", "role": "Mentor", "personality": "Wise, Calm, focused on long term growth."},
            "mom": {
                "name": "Mother",
                "role": "Supporter",
                "personality": "Caring, worried about health, nagging but sweet.",
            },
        }
        return profiles.get(npc_id.lower())

    def _get_context(self, user_id: str, npc_id: str) -> List[str]:
        # Placeholder for graph retrieval
        return []

    async def _update_relationship(self, user_id: str, npc_id: str, delta: int):
        # Always update last_interaction, even if delta is 0
        try:
            # Ensure User and NPC nodes exist, then link them
            # Using Cypher Update
            ts = int(time.time())
            query = (
                f"MERGE (u:User {{id: '{user_id}'}}) "
                f"MERGE (n:NPC {{id: '{npc_id}'}}) "
                f"MERGE (u)-[r:KNOWS]->(n) "
                f"ON CREATE SET u.name = 'Unknown', n.name = '{npc_id}', r.intimacy = 0, r.last_interaction = {ts} "
                f"ON MATCH SET r.intimacy = r.intimacy + {delta}, r.last_interaction = {ts}"
            )
            await self.kuzu.query(query)
        except Exception as e:
            logger.error(f"Failed to update relationship: {e}")

    def _log_interaction(self, user_id: str, npc_id: str, u_text: str, n_text: str):
        # MVP: Skip detailed logging to avoid graph explosion unless meaningful.
        pass


social_service = SocialService()
