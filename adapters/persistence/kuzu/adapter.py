import kuzu
import os
import logging
import uuid
from datetime import datetime
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
        if os.path.dirname(self.db_path):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _initialize_schema(self):
        """Idempotent schema initialization with expanded schema"""
        try:
            # Check if User table exists
            self.conn.execute("MATCH (u:User) RETURN count(u) LIMIT 1")
        except RuntimeError:
            logger.info("Initializing KuzuDB Schema...")
            try:
                # Core Node Tables
                self.conn.execute("CREATE NODE TABLE User(name STRING, PRIMARY KEY (name))")
                self.conn.execute("CREATE NODE TABLE NPC(name STRING, role STRING, mood STRING, PRIMARY KEY (name))")
                self.conn.execute("CREATE NODE TABLE Concept(name STRING, description STRING, PRIMARY KEY (name))")
                self.conn.execute("CREATE NODE TABLE Quest(id STRING, title STRING, status STRING, PRIMARY KEY (id))")
                self.conn.execute("CREATE NODE TABLE Location(name STRING, description STRING, PRIMARY KEY (name))")
                self.conn.execute("CREATE NODE TABLE Event(id STRING, type STRING, timestamp STRING, metadata STRING, PRIMARY KEY (id))")
                
                # NPC Relationships
                self.conn.execute("CREATE REL TABLE HATES(FROM NPC TO Concept)")
                self.conn.execute("CREATE REL TABLE LIKES(FROM NPC TO Concept)")
                self.conn.execute("CREATE REL TABLE CARES_ABOUT(FROM NPC TO Concept)")
                self.conn.execute("CREATE REL TABLE LOCATED_AT(FROM NPC TO Location)")
                
                # User Relationships
                self.conn.execute("CREATE REL TABLE INTERACTED_WITH(FROM User TO NPC, timestamp STRING)")
                self.conn.execute("CREATE REL TABLE COMPLETED(FROM User TO Quest, timestamp STRING)")
                self.conn.execute("CREATE REL TABLE FAILED(FROM User TO Quest, timestamp STRING)")
                self.conn.execute("CREATE REL TABLE VISITED(FROM User TO Location, count INT)")
                
                # Event Relationships
                self.conn.execute("CREATE REL TABLE TRIGGERED_BY(FROM Event TO User)")
                self.conn.execute("CREATE REL TABLE WITNESSED(FROM NPC TO Event)")

                # Seed NPCs
                self._seed_initial_data()
                logger.info("Schema Initialized.")
            except Exception as e:
                logger.error(f"Schema Init Failed: {e}")

    def _seed_initial_data(self):
        """Seed NPCs and initial concepts"""
        # Concepts
        concepts = [
            ("Procrastination", "拖延任務和責任"),
            ("Discipline", "自律和堅持"),
            ("Exercise", "身體鍛鍊"),
            ("Learning", "學習新知識"),
            ("Meditation", "冥想和內省"),
            ("Action", "立即行動"),
            ("Laziness", "懶惰和懈怠"),
            ("Strategy", "策略思考"),
        ]
        for name, desc in concepts:
            self.conn.execute(f"CREATE (c:Concept {{name: '{name}', description: '{desc}'}})")
        
        # NPCs with personalities
        npcs = [
            ("Viper", "Strict Mentor", "Stern"),
            ("Sage", "Wise Elder", "Calm"),
            ("Ember", "Energetic Coach", "Excited"),
            ("Shadow", "Mysterious Guide", "Neutral"),
        ]
        for name, role, mood in npcs:
            self.conn.execute(f"CREATE (n:NPC {{name: '{name}', role: '{role}', mood: '{mood}'}})")
        
        # NPC Preferences
        preferences = [
            ("Viper", "HATES", "Procrastination"),
            ("Viper", "LIKES", "Discipline"),
            ("Viper", "LIKES", "Exercise"),
            ("Sage", "LIKES", "Learning"),
            ("Sage", "LIKES", "Meditation"),
            ("Sage", "HATES", "Laziness"),
            ("Ember", "LIKES", "Action"),
            ("Ember", "LIKES", "Exercise"),
            ("Ember", "HATES", "Laziness"),
            ("Shadow", "LIKES", "Strategy"),
            ("Shadow", "CARES_ABOUT", "Learning"),
        ]
        for npc, rel, concept in preferences:
            self.conn.execute(
                f"MATCH (n:NPC {{name: '{npc}'}}), (c:Concept {{name: '{concept}'}}) "
                f"CREATE (n)-[:{rel}]->(c)"
            )
        
        # Default User
        self.conn.execute("CREATE (u:User {name: 'Player'})")
        
        logger.info("Seeded initial graph data")

    def query(self, cypher: str) -> List[Any]:
        """Execute a Cypher query and return results as list of rows"""
        result = self.conn.execute(cypher)
        output = []
        while result.has_next():
            row = result.get_next()
            output.append(row)
        return output

    def add_node(self, label: str, properties: Dict[str, Any]) -> bool:
        """Add a node with given label and properties"""
        try:
            props_str = ", ".join([f"{k}: '{v}'" for k, v in properties.items()])
            cypher = f"CREATE (n:{label} {{{props_str}}})"
            self.conn.execute(cypher)
            return True
        except Exception as e:
            logger.error(f"Failed to add node: {e}")
            return False

    def add_relationship(
        self, 
        from_label: str, 
        from_key: str, 
        rel_type: str, 
        to_label: str, 
        to_key: str,
        properties: Dict[str, Any] = None
    ) -> bool:
        """Create a relationship between two nodes"""
        try:
            props_str = ""
            if properties:
                props_str = " {" + ", ".join([f"{k}: '{v}'" for k, v in properties.items()]) + "}"
            
            cypher = (
                f"MATCH (a:{from_label} {{name: '{from_key}'}}), "
                f"(b:{to_label} {{name: '{to_key}'}}) "
                f"CREATE (a)-[:{rel_type}{props_str}]->(b)"
            )
            self.conn.execute(cypher)
            return True
        except Exception as e:
            logger.error(f"Failed to add relationship: {e}")
            return False

    def get_npc_context(self, npc_name: str) -> Dict[str, Any]:
        """Get full context for an NPC including personality, mood, likes, hates"""
        try:
            # Get NPC base info
            result = self.conn.execute(
                f"MATCH (n:NPC {{name: '{npc_name}'}}) RETURN n.name, n.role, n.mood"
            )
            npc_data = {"name": npc_name, "role": "", "mood": "", "likes": [], "hates": [], "cares_about": []}
            
            if result.has_next():
                row = result.get_next()
                npc_data["name"] = row[0]
                npc_data["role"] = row[1]
                npc_data["mood"] = row[2]
            
            # Get likes
            likes_result = self.conn.execute(
                f"MATCH (n:NPC {{name: '{npc_name}'}})-[:LIKES]->(c:Concept) RETURN c.name"
            )
            while likes_result.has_next():
                npc_data["likes"].append(likes_result.get_next()[0])
            
            # Get hates
            hates_result = self.conn.execute(
                f"MATCH (n:NPC {{name: '{npc_name}'}})-[:HATES]->(c:Concept) RETURN c.name"
            )
            while hates_result.has_next():
                npc_data["hates"].append(hates_result.get_next()[0])
            
            # Get cares_about
            cares_result = self.conn.execute(
                f"MATCH (n:NPC {{name: '{npc_name}'}})-[:CARES_ABOUT]->(c:Concept) RETURN c.name"
            )
            while cares_result.has_next():
                npc_data["cares_about"].append(cares_result.get_next()[0])
            
            return npc_data
        except Exception as e:
            logger.error(f"Failed to get NPC context: {e}")
            return {"name": npc_name, "role": "Unknown", "mood": "Neutral", "likes": [], "hates": [], "cares_about": []}

    def record_user_event(self, user_id: str, event_type: str, metadata: Dict[str, Any]) -> bool:
        """Record a user event in the graph for memory/context"""
        try:
            event_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now().isoformat()
            metadata_str = str(metadata).replace("'", "\\'")
            
            # Ensure user exists
            self.conn.execute(f"MERGE (u:User {{name: '{user_id}'}})")
            
            # Create event
            self.conn.execute(
                f"CREATE (e:Event {{id: '{event_id}', type: '{event_type}', "
                f"timestamp: '{timestamp}', metadata: '{metadata_str}'}})"
            )
            
            # Link event to user
            self.conn.execute(
                f"MATCH (e:Event {{id: '{event_id}'}}), (u:User {{name: '{user_id}'}}) "
                f"CREATE (e)-[:TRIGGERED_BY]->(u)"
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to record user event: {e}")
            return False

    def get_user_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent user events/interactions from graph"""
        try:
            result = self.conn.execute(
                f"MATCH (e:Event)-[:TRIGGERED_BY]->(u:User {{name: '{user_id}'}}) "
                f"RETURN e.id, e.type, e.timestamp, e.metadata "
                f"ORDER BY e.timestamp DESC LIMIT {limit}"
            )
            
            events = []
            while result.has_next():
                row = result.get_next()
                events.append({
                    "id": row[0],
                    "type": row[1],
                    "timestamp": row[2],
                    "metadata": row[3]
                })
            
            return events
        except Exception as e:
            logger.error(f"Failed to get user history: {e}")
            return []
