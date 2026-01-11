from typing import Dict, Any, List
from adapters.persistence.kuzu.adapter import KuzuAdapter


class GraphService:
    def __init__(self):
        # Lazy initialization to prevent lock issues on import
        self._adapter = None

    @property
    def adapter(self) -> KuzuAdapter:
        if self._adapter is None:
            self._adapter = KuzuAdapter()
        return self._adapter

    def query(self, cypher: str):
        """Execute Cypher query with cursor-like wrapper for backward compatibility"""
        return KuzuCursorWrapper(self.adapter.query(cypher))
    
    def get_npc_context(self, npc_name: str) -> Dict[str, Any]:
        """Get full context for an NPC including personality, mood, likes, hates"""
        return self.adapter.get_npc_context(npc_name)
    
    def get_all_npcs(self) -> List[Dict[str, Any]]:
        """Get all NPCs with their full context"""
        result = self.adapter.query("MATCH (n:NPC) RETURN n.name")
        npcs = []
        for row in result:
            npc_name = row[0]
            npcs.append(self.get_npc_context(npc_name))
        return npcs
    
    def record_event(self, user_id: str, event_type: str, metadata: Dict[str, Any] = None) -> bool:
        """Record a user event in the graph"""
        return self.adapter.record_user_event(user_id, event_type, metadata or {})
    
    def get_user_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent user events from graph memory"""
        return self.adapter.get_user_history(user_id, limit)
    
    def add_user_npc_interaction(self, user_id: str, npc_name: str) -> bool:
        """Record that a user interacted with an NPC"""
        from datetime import datetime
        return self.adapter.add_relationship(
            "User", user_id, "INTERACTED_WITH", "NPC", npc_name,
            {"timestamp": datetime.now().isoformat()}
        )
    
    def add_quest_dependency(self, child_quest_id: str, parent_quest_id: str) -> bool:
        """
        Add a dependency between two quests: Child REQUIRES Parent.
        """
        return self.adapter.add_quest_dependency(child_quest_id, parent_quest_id)
    
    def get_unlockable_templates(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get quest templates that are unlockable for the user (prerequisites met but not completed).
        """
        return self.adapter.get_unlockable_templates(user_id)


class KuzuCursorWrapper:
    """Wrapper to provide cursor-like interface for backward compatibility"""
    def __init__(self, data):
        self.data = data
        self.index = 0
        
    def has_next(self):
        return self.index < len(self.data)
        
    def get_next(self):
        if self.has_next():
            val = self.data[self.index]
            self.index += 1
            return val
        return None


graph_service = GraphService()
