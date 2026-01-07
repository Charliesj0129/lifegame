from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional

class GraphPort(ABC):
    @abstractmethod
    def query(self, cypher: str) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return a list of dictionaries.
        """
        pass
