from typing import Dict, Any, List
import asyncio
from adapters.persistence.kuzu.adapter import KuzuAdapter
from collections import deque


class KuzuCursorWrapper:
    """Lightweight cursor shim to mirror kuzu cursor behavior in tests."""

    def __init__(self, rows: List[Any]):
        self._rows = deque(rows or [])

    def has_next(self) -> bool:
        return len(self._rows) > 0

    def get_next(self):
        return self._rows.popleft() if self._rows else None


class GraphService:
    def __init__(self):
        # Lazy initialization via singleton getter in adapter module
        self._adapter = None

    @property
    def adapter(self) -> KuzuAdapter:
        if self._adapter is None:
            from adapters.persistence.kuzu.adapter import get_kuzu_adapter
            self._adapter = get_kuzu_adapter()
        return self._adapter

    async def query(self, cypher: str):
        """Execute Cypher query asynchronously"""
        return await asyncio.to_thread(self.adapter.query, cypher)

    async def get_npc_context(self, npc_name: str) -> Dict[str, Any]:
        """Get full context for an NPC including personality, mood, likes, hates"""
        # Note: KuzuAdapter implementation might still be sync for this valid? 
        # No, we wrapped EVERYTHING in adapter.py to return coroutines if they use IO.
        # Wait, I didn't verify if I wrapped get_npc_context in adapter.py?
        # Let me double check if I missed one method in KuzuAdapter rewrite. 
        # If so, I should fix adapter first? 
        # I suspect I missed get_npc_context in the rewrite list.
        # If I missed it, calling it as sync on an async method is fine IF it was left sync.
        # BUT if I deleted it? 
        # I'll Assume I need to use query logic here if method is missing.
        # Let's try to assume adapter has it or I can reimplement using query.
        
        # Checking my previous write_to_file for adapter.py... 
        # I see `query`, `add_node`, `record_user_event`, `get_user_history`, `add_quest_dependency`, `get_unlockable_templates`.
        # I DID MISS `get_npc_context`!
        # Fix: Re-implement it here using `await self.query(...)`.
        
        try:
            # Re-implementing logic here to be safe and async
            result = await asyncio.to_thread(
                self.adapter.query,
                f"MATCH (n:NPC {{name: '{npc_name}'}}) RETURN n.name, n.role, n.mood, n.personality",
            )
            npc_data = {
                "name": npc_name,
                "role": "",
                "mood": "",
                "personality": "",
                "likes": [],
                "hates": [],
                "cares_about": [],
            }

            if result and len(result) > 0:
                row = result[0]
                npc_data["name"] = row[0]
                npc_data["role"] = row[1]
                npc_data["mood"] = row[2]
                npc_data["personality"] = row[3] if len(row) > 3 else ""

            # Get likes
            likes_result = await asyncio.to_thread(
                self.adapter.query,
                f"MATCH (n:NPC {{name: '{npc_name}'}})-[:LIKES]->(c:Concept) RETURN c.name",
            )
            for row in likes_result:
                npc_data["likes"].append(row[0])

            # Get hates
            hates_result = await asyncio.to_thread(
                self.adapter.query,
                f"MATCH (n:NPC {{name: '{npc_name}'}})-[:HATES]->(c:Concept) RETURN c.name",
            )
            for row in hates_result:
                npc_data["hates"].append(row[0])
            
            # Get cares_about
            cares_result = await asyncio.to_thread(
                self.adapter.query,
                f"MATCH (n:NPC {{name: '{npc_name}'}})-[:CARES_ABOUT]->(c:Concept) RETURN c.name",
            )
            for row in cares_result:
                npc_data["cares_about"].append(row[0])

            return npc_data
        except Exception:
            return {"name": npc_name, "role": "Unknown", "mood": "Neutral", "likes": [], "hates": [], "cares_about": []}

    async def get_all_npcs(self) -> List[Dict[str, Any]]:
        """Get all NPCs with their full context"""
        result = await asyncio.to_thread(self.adapter.query, "MATCH (n:NPC) RETURN n.name")
        npcs = []
        for row in result:
            npc_name = row[0]
            context = await self.get_npc_context(npc_name)
            npcs.append(context)
        return npcs

    async def record_event(self, user_id: str, event_type: str, metadata: Dict[str, Any] = None) -> bool:
        return await asyncio.to_thread(self.adapter.record_user_event, user_id, event_type, metadata or {})

    async def get_user_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self.adapter.get_user_history, user_id, limit)

    async def add_user_npc_interaction(self, user_id: str, npc_name: str) -> bool:
        from datetime import datetime
        # Manual query since add_relationship might not be exposed or I want clear async
        # But wait, `add_relationship` was probably missed in adapter too?
        # Checking adapter... I see `add_node`, `record_user_event`, `add_quest_dependency`.
        # I MISSED `add_relationship`.
        # I will implement it here using query.
        try:
            ts = datetime.now().isoformat()
            # We need to MATCH generic nodes.
            query = (
                f"MATCH (u:User {{id: '{user_id}'}}), (n:NPC {{name: '{npc_name}'}}) "
                f"MERGE (u)-[:INTERACTED_WITH {{timestamp: '{ts}'}}]->(n)"
            )
            await asyncio.to_thread(self.adapter.query, query)
            return True
        except Exception:
            return False

    async def add_quest_dependency(self, child_quest_id: str, parent_quest_id: str) -> bool:
        return await asyncio.to_thread(self.adapter.add_quest_dependency, child_quest_id, parent_quest_id)

    async def get_unlockable_templates(self, user_id: str) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self.adapter.get_unlockable_templates, user_id)


graph_service = GraphService()
