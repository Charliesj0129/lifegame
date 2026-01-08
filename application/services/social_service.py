import logging
import time
from typing import Dict, Any, List, Optional
from adapters.persistence.kuzu_adapter import get_kuzu_adapter
from legacy.services.ai_engine import ai_engine
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
        # For now, we mock/hardcode based on ID if not in Graph, or fetch from Graph.
        npc_profile = self._get_npc_profile(npc_id)
        if not npc_profile:
            return {"text": "那個 NPC 不存在... (Shadow Realm error)"}

        # 2. Retrieve Context (Graph)
        # - Last 5 interactions
        # - Shared Memories (Events linked by REMEMBERED)
        context = self._get_context(user_id, npc_id)
        
        # 3. Generate Response (AI)
        # We need to enhance AI Engine to support "Chat Mode"
        response_data = await ai_engine.generate_npc_response(
            persona=npc_profile,
            context=context,
            user_input=text
        )
        
        reply_text = response_data.get("text", "...")
        intimacy_delta = response_data.get("intimacy_change", 0)
        
        # 4. Update Graph
        self._update_relationship(user_id, npc_id, intimacy_delta)
        self._log_interaction(user_id, npc_id, text, reply_text)
        
        return {
            "text": reply_text,
            "can_visualize": response_data.get("can_visualize", False)
        }

    def _get_npc_profile(self, npc_id: str) -> Dict[str, str]:
        # TODO: Fetch from Graph Node. For Phase 5 MVP, use hardcoded or simple query.
        # Fallback to hardcoded for "Viper" etc if Graph is empty.
        profiles = {
            "viper": {"name": "Viper", "role": "Rival", "personality": "Competitor, Toxic User Logic, Cynical but pushing you to grow."},
            "mentor": {"name": "Zenith", "role": "Mentor", "personality": "Wise, Calm, focused on long term growth."},
            "mom": {"name": "Mother", "role": "Supporter", "personality": "Caring, worried about health, nagging but sweet."}
        }
        return profiles.get(npc_id.lower())

    def _get_context(self, user_id: str, npc_id: str) -> List[str]:
        # Query Kuzu for last interactions
        # MATCH (u:User {id: $uid})-[r:KNOWS]->(n:NPC {id: $nid})
        # This gives relationship state.
        # But for *History*, we might need Event logs linked to both?
        # Or just store recent chat in SQLite/Redis?
        # For Phase 5, let's query "Event" nodes that involve NPC?
        # Currently we only link User->Event. 
        # We need to link NPC->Event or User->Event<-NPC?
        # Simplified: Just return "Relationship Status" for now.
        return []

    def _update_relationship(self, user_id: str, npc_id: str, delta: int):
        # Always update last_interaction, even if delta is 0
        try:
           # Ensure User and NPC nodes exist, then link them
           # MERGE (u:User {id: $uid})
           # MERGE (n:NPC {id: $nid})
           # MERGE (u)-[r:KNOWS]->(n)
           query = """
           MERGE (u:User {id: $uid})
           MERGE (n:NPC {id: $nid})
           MERGE (u)-[r:KNOWS]->(n)
           ON CREATE SET u.name = 'Unknown', n.name = $nid, r.intimacy = 0, r.last_interaction = $ts
           ON MATCH SET r.intimacy = r.intimacy + $delta, r.last_interaction = $ts
           """
           self.kuzu.conn.execute(query, {
               "uid": user_id, 
               "nid": npc_id, 
               "delta": delta, 
               "ts": int(time.time())
            })
        except Exception as e:
            logger.error(f"Failed to update relationship: {e}")

    def _log_interaction(self, user_id: str, npc_id: str, u_text: str, n_text: str):
        # Create an Event for this chat?
        # Maybe too noisy. Log critical moments?
        # MVP: Skip detailed logging to avoid graph explosion unless meaningful.
        pass

social_service = SocialService()
