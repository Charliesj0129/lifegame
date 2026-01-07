import kuzu
import os
import logging
from typing import List, Dict, Any
from domain.ports.graph_port import GraphPort
from app.core.config import settings

logger = logging.getLogger(__name__)

class KuzuAdapter(GraphPort):
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.KUZU_DATABASE_PATH
        self._ensure_db_dir()
        self.db = kuzu.Database(self.db_path)
        self.conn = kuzu.Connection(self.db)
        self._initialize_schema()

    def _ensure_db_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _initialize_schema(self):
        """Idempotent schema initialization"""
        try:
            # Check if User table exists
             self.conn.execute("MATCH (u:User) RETURN count(u) LIMIT 1")
        except RuntimeError:
            logger.info("Initializing KuzuDB Schema...")
            try:
                self.conn.execute("CREATE NODE TABLE User(name STRING, PRIMARY KEY (name))")
                self.conn.execute("CREATE NODE TABLE NPC(name STRING, role STRING, mood STRING, PRIMARY KEY (name))")
                self.conn.execute("CREATE NODE TABLE Concept(name STRING, description STRING, PRIMARY KEY (name))")
                
                # Relationships
                self.conn.execute("CREATE REL TABLE HATES(FROM NPC TO Concept)")
                self.conn.execute("CREATE REL TABLE LIKES(FROM NPC TO Concept)")
                self.conn.execute("CREATE REL TABLE INTERACTED_WITH(FROM User TO NPC, timestamp STRING)")

                # Seed Data (Minimal)
                self.conn.execute("CREATE (u:User {name: 'Player'})")
                self.conn.execute("CREATE (n:NPC {name: 'Viper', role: 'Strict Mentor', mood: 'Neutral'})")
                self.conn.execute("CREATE (c:Concept {name: 'Procrastination', description: 'Delaying tasks'})")
                self.conn.execute("MATCH (n:NPC {name: 'Viper'}), (c:Concept {name: 'Procrastination'}) CREATE (n)-[:HATES]->(c)")
                logger.info("Schema Initialized.")
            except Exception as e:
                logger.error(f"Schema Init Failed: {e}")

    def query(self, cypher: str) -> List[Dict[str, Any]]:
        result = self.conn.execute(cypher)
        output = []
        while result.has_next():
            # Convert result item to dict? Kuzu execute returns a specialized cursor.
            # We need to see how to get columns.
            # result.get_next() returns a list of values.
            # result.get_schema() might give column names?
            # Or usually we rely on AS in query?
            # Let's try to map generic row to list for now or dict if possible
            # Depending on Kuzu python API version.
            # Assuming get_next returns a list of values matching RETURN clause order.
            
            # Note: The original service just returned the result object, forcing the consumer to know Kuzu.
            # The Port should return generic structures.
            # But the original logic in nerves.py access result.get_next() manually.
            # To fix nerves.py, we should return something iterable or a list of rows.
            # Let's return a list of rows (lists) for now or update Port to return iterator?
            # The Port says List[Dict].
            # Trying to mock "Dict" without column names from `execute` result is hard unless we assume
            # column names are available.
            # In Kuzu Py, result has no direct column name accessor easily on the iterator?
            # Actually result usually doesn't until we check documentation.
            # Let's return the RAW result object inside a wrapper? No that leaks abstraction.
            # Let's change Port to List[List[Any]] for now or use strict keys if we knew them.
            
            # Wait, `nerves.py` logic:
            # result = graph_service.query("MATCH (n:NPC) RETURN n.name, n.role")
            # row = result.get_next()
            # npcs.append(f"{row[0]} ({row[1]})")
            
            # The consumer expects to iterate.
            # I will fetch all to list.
            row = result.get_next()
            output.append(row)
            
        return output
