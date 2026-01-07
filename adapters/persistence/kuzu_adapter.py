import kuzu
import logging
import os
import shutil
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class KuzuAdapter:
    def __init__(self, db_path: str = "./data/lifegame_graph"):
        self.db_path = db_path
        self.db = None
        self.conn = None
        self._initialize()

    def _initialize(self):
        """Initialize KuzuDB and Schema."""
        try:
            # Ensure PARENT directory exists
            parent_dir = os.path.dirname(self.db_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            
            # Do NOT create db_path directory itself; Kuzu handles it
            
            self.db = kuzu.Database(self.db_path)
            self.conn = kuzu.Connection(self.db)
            self._create_schema()
            logger.info(f"KuzuDB initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize KuzuDB: {e}", exc_info=True)
            raise

    def _create_schema(self):
        """Define the Graph Schema."""
        # 1. User Node
        try:
            self.conn.execute("CREATE NODE TABLE User(id STRING, name STRING, PRIMARY KEY (id))")
        except RuntimeError:
            pass  # Already exists

        # 2. Event Node
        try:
            self.conn.execute("""
                CREATE NODE TABLE Event(
                    id STRING, 
                    type STRING, 
                    content STRING, 
                    timestamp INT64, 
                    PRIMARY KEY (id)
                )
            """)
        except RuntimeError:
            pass

        # 3. Fact Node (Knowledge Shards)
        try:
            self.conn.execute("CREATE NODE TABLE Fact(id STRING, topic STRING, content STRING, PRIMARY KEY (id))")
        except RuntimeError:
            pass

        # 4. Quest Node
        try:
            self.conn.execute("CREATE NODE TABLE Quest(id STRING, title STRING, status STRING, PRIMARY KEY (id))")
        except RuntimeError:
            pass

        # Relationships
        rels = [
            "CREATE REL TABLE PERFORMED(FROM User TO Event)",
            "CREATE REL TABLE GENERATED(FROM Event TO Fact)",
            "CREATE REL TABLE RELATED_TO(FROM Fact TO Fact)",
            "CREATE REL TABLE HAS_QUEST(FROM User TO Quest)"
        ]
        
        for rel_cypher in rels:
            try:
                self.conn.execute(rel_cypher)
            except RuntimeError:
                pass

    def add_user_if_not_exists(self, user_id: str, name: str = "Unknown"):
        try:
            self.conn.execute(
                "MERGE (u:User {id: $id, name: $name}) RETURN u",
                {"id": user_id, "name": name}
            )
        except Exception as e:
            logger.error(f"Graph Error (Add User): {e}")

    def add_event(self, user_id: str, event_id: str, event_type: str, content: str, timestamp: int):
        """Log an event and link it to the user."""
        try:
            # Create Event Link
            self.conn.execute(
                """
                MERGE (e:Event {id: $eid, type: $etype, content: $content, timestamp: $ts})
                """,
                {"eid": event_id, "etype": event_type, "content": content, "ts": timestamp}
            )
            
            # Link User -> Event
            self.conn.execute(
                """
                MATCH (u:User {id: $uid}), (e:Event {id: $eid})
                MERGE (u)-[:PERFORMED]->(e)
                """,
                {"uid": user_id, "eid": event_id}
            )
        except Exception as e:
            logger.error(f"Graph Error (Add Event): {e}")

    def query_recent_context(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent events for a user."""
        try:
            response = self.conn.execute(
                """
                MATCH (u:User {id: $uid})-[:PERFORMED]->(e:Event)
                RETURN e.type, e.content, e.timestamp
                ORDER BY e.timestamp DESC
                LIMIT $limit
                """,
                {"uid": user_id, "limit": limit}
            )
            columns = ["type", "content", "timestamp"]
            results = []
            while response.has_next():
                row = response.get_next()
                if row:
                    results.append(dict(zip(columns, row)))
            return results
        except Exception as e:
            logger.error(f"Graph Error (Query Context): {e}")
            return []

_kuzu_instance = None

def get_kuzu_adapter() -> KuzuAdapter:
    global _kuzu_instance
    if _kuzu_instance is None:
        _kuzu_instance = KuzuAdapter()
    return _kuzu_instance
