from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional


class GraphPort(ABC):
    @abstractmethod
    def query(self, cypher: str) -> List[Any]:
        """
        Execute a Cypher query and return results.
        """
        pass

    @abstractmethod
    def add_node(self, label: str, properties: Dict[str, Any]) -> bool:
        """
        Add a node with given label and properties.
        """
        pass

    @abstractmethod
    def add_relationship(
        self,
        from_label: str,
        from_key: str,
        rel_type: str,
        to_label: str,
        to_key: str,
        properties: Dict[str, Any] = None,
        from_key_field: str = "name",
        to_key_field: str = "name",
    ) -> bool:
        """
        Create a relationship between two nodes.

        Args:
            from_key_field: Field to match for source node ('name' or 'id')
            to_key_field: Field to match for target node ('name' or 'id')
        """
        pass

    @abstractmethod
    def get_npc_context(self, npc_name: str) -> Dict[str, Any]:
        """
        Get full context for an NPC including personality, mood, likes, hates.
        """
        pass

    @abstractmethod
    def record_user_event(self, user_id: str, event_type: str, metadata: Dict[str, Any]) -> bool:
        """
        Record a user event in the graph for memory/context.
        """
        pass

    @abstractmethod
    def get_user_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent user events/interactions from graph.
        """
        pass

    @abstractmethod
    def add_quest_dependency(self, child_quest_id: str, parent_quest_id: str) -> bool:
        """
        Add a dependency between two quests, where the child quest requires the parent quest to be completed.
        """
        pass

    @abstractmethod
    def get_unlockable_templates(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get a list of unlockable templates for a given user.
        """
        pass
