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
        """Idempotent schema initialization"""
        try:
            # 1. Verify Schema Integrity (Self-Healing)
            # Check if User table exists and has correct PK
            # user_valid = False  <-- Removed unused variable
            try:
                # Check for table existence
                self.conn.execute("MATCH (u:User) RETURN count(u) LIMIT 1")

                # Check PK (simplistic check: try MERGE with name)
                # If PK is wrong (id), his will fail, confirming corruption
                self.conn.execute("MERGE (u:User {name: 'SchemaCheck'})")
                # user_valid = True  <-- Removed unused variable
            except Exception:
                logger.warning("User table corrupted or missing (Wrong PK?). Recreating...")
                try:
                    self.conn.execute("DROP TABLE User")
                except Exception:
                    pass

            # 2. Schema Creation / Repair
            def safe_create(query):
                try:
                    self.conn.execute(query)
                except RuntimeError as re:
                    if "already exists" in str(re):
                        pass
                    else:
                        logger.warning(f"Failed to exec {query}: {re}")

            # Re-create User if needed
            safe_create("CREATE NODE TABLE User(id STRING, name STRING, PRIMARY KEY (id))")

            # Create other tables (Safe if exist)
            safe_create(
                "CREATE NODE TABLE NPC(id STRING, name STRING, role STRING, personality STRING, mood STRING, PRIMARY KEY (id))"
            )
            safe_create("CREATE NODE TABLE Concept(name STRING, description STRING, PRIMARY KEY (name))")
            safe_create("CREATE NODE TABLE Quest(id STRING, title STRING, status STRING, PRIMARY KEY (id))")
            safe_create("CREATE NODE TABLE Location(name STRING, description STRING, PRIMARY KEY (name))")
            safe_create(
                "CREATE NODE TABLE Event(id STRING, type STRING, content STRING, timestamp INT64, metadata STRING, PRIMARY KEY (id))"
            )

            # Relationships
            safe_create("CREATE REL TABLE HATES(FROM NPC TO Concept)")
            safe_create("CREATE REL TABLE LIKES(FROM NPC TO Concept)")
            safe_create("CREATE REL TABLE CARES_ABOUT(FROM NPC TO Concept)")
            safe_create("CREATE REL TABLE LOCATED_AT(FROM NPC TO Location)")

            safe_create("CREATE REL TABLE INTERACTED_WITH(FROM User TO NPC, timestamp STRING)")
            safe_create("CREATE REL TABLE COMPLETED(FROM User TO Quest, timestamp STRING)")
            safe_create("CREATE REL TABLE FAILED(FROM User TO Quest, timestamp STRING)")
            safe_create("CREATE REL TABLE VISITED(FROM User TO Location, count INT)")

            safe_create("CREATE REL TABLE TRIGGERED_BY(FROM Event TO User)")
            safe_create("CREATE REL TABLE PERFOMRED(FROM User TO Event)")  # Alias for TRIGGERED_BY or specific action?
            safe_create("CREATE REL TABLE WITNESSED(FROM NPC TO Event)")
            safe_create("CREATE REL TABLE INVOLVED(FROM Event TO NPC)")

            safe_create("CREATE REL TABLE REQUIRES(FROM Quest TO Quest)")

            # Phase 5 Social Engine
            safe_create("CREATE REL TABLE KNOWS(FROM User TO NPC, intimacy INT64, last_interaction INT64)")
            safe_create("CREATE REL TABLE REMEMBERED(FROM NPC TO Event)")
            safe_create(
                "CREATE REL TABLE PERFORMED(FROM User TO Event)"
            )  # Replaces/Aligns with TRIGGERED_BY? keeping both for safety or aligning.
            # safe_create("CREATE REL TABLE GENERATED(FROM Event TO Fact)") # If Facts are used
            # safe_create("CREATE REL TABLE RELATED_TO(FROM Fact TO Fact)")

            # Seed Data (Idempotent MERGE)
            self._seed_initial_data()
            logger.info("Schema Initialized (Integrity Checked).")

        except Exception as e:
            logger.error(f"Schema Init Failed: {e}")

    def add_quest_dependency(self, child_quest_id: str, parent_quest_id: str) -> bool:
        """
        Add a dependency: Child REQUIRES Parent.
        (Child)-[:REQUIRES]->(Parent)
        """
        try:
            # Ensure nodes exist (assuming IDs are pre-seeded or we merge them)
            # Creating dummy nodes if they don't exist to allow relationship
            self.conn.execute(f"MERGE (c:Quest {{id: '{child_quest_id}'}})")
            self.conn.execute(f"MERGE (p:Quest {{id: '{parent_quest_id}'}})")

            self.conn.execute(
                f"MATCH (c:Quest {{id: '{child_quest_id}'}}), (p:Quest {{id: '{parent_quest_id}'}}) "
                f"CREATE (c)-[:REQUIRES]->(p)"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add quest dependency: {e}")
            return False

    def get_unlockable_templates(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Find Quests where:
        1. User has NOT completed them.
        2. User HAS completed ALL prerequisites.
        """
        try:
            # Cypher Logic:
            # Find candidate Quest `t`
            # WHERE NOT (User)-[:COMPLETED]->(t)
            # AND ALL `req` in (t)-[:REQUIRES]->(req) HAVE (User)-[:COMPLETED]->(req)

            # Kuzu Support Check:
            # Does Kuzu support EXISTS pattern in WHERE? Yes.
            # Does Kuzu support ALL list comprehension? Partial.
            # Alternative: Return candidates and filter in python if query is too complex,
            # but let's try a robust query.

            # Simple approach:
            # 1. Get ALL quests `q`
            # 2. Filter `q` not completed by user.
            # 3. For each `q`, check if it has prereqs.
            # 4. If prereqs exist, check if ALL are completed.

            # Optimised Query:
            query = (
                f"MATCH (q:Quest) "
                f"WHERE NOT EXISTS {{ MATCH (u:User {{name: '{user_id}'}})-[:COMPLETED]->(q) }} "
                f"RETURN q.id, q.title"
            )
            candidates = self.query(query)

            unlockables = []
            for row in candidates:
                q_id, q_title = row[0], row[1]

                # Check prerequisites
                prereqs_query = f"MATCH (q:Quest {{id: '{q_id}'}})-[:REQUIRES]->(req:Quest) RETURN req.id"
                prereqs = [r[0] for r in self.query(prereqs_query)]

                if not prereqs:
                    # No prereqs = Base quest, always unlocked?
                    # Or maybe base quests are unlocked by default.
                    # Let's include them.
                    unlockables.append({"id": q_id, "title": q_title, "type": "BASE"})
                    continue

                # Check if all prereqs are completed
                completed_count = 0
                for pid in prereqs:
                    check_done = (
                        f"MATCH (u:User {{name: '{user_id}'}})-[:COMPLETED]->(q:Quest {{id: '{pid}'}}) RETURN count(q)"
                    )
                    if self.query(check_done)[0][0] > 0:
                        completed_count += 1

                if completed_count == len(prereqs):
                    unlockables.append({"id": q_id, "title": q_title, "type": "CHAIN_UNLOCK"})

            return unlockables

        except Exception as e:
            logger.error(f"Failed to get unlockables: {e}")
            return []

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
            self.conn.execute(f"MERGE (c:Concept {{name: '{name}'}}) ON CREATE SET c.description = '{desc}'")

        # NPCs with personalities
        # ID can be name in lowercase or specific UUID. Let's use name.lower() as ID.
        npcs = [
            ("Viper", "Strict Mentor", "Stern", "Competitor"),
            ("Sage", "Wise Elder", "Calm", "Guide"),
            ("Ember", "Energetic Coach", "Excited", "Support"),
            ("Shadow", "Mysterious Guide", "Neutral", "Observer"),
        ]
        for name, role, mood, personality in npcs:
            nid = name.lower()
            self.conn.execute(
                f"MERGE (n:NPC {{id: '{nid}'}}) "
                f"ON CREATE SET n.name = '{name}', n.role = '{role}', n.mood = '{mood}', n.personality = '{personality}' "
                f"ON MATCH SET n.role = '{role}', n.mood = '{mood}'"
            )

        # NPC Preferences (Link by ID? or Name if non-primary keys match?)
        # Relationships use MATCH.
        # MATCH (n:NPC {id: 'viper'}), (c:Concept {name: '...'})
        preferences = [
            ("viper", "HATES", "Procrastination"),
            ("viper", "LIKES", "Discipline"),
            ("viper", "LIKES", "Exercise"),
            ("sage", "LIKES", "Learning"),
            ("sage", "LIKES", "Meditation"),
            ("sage", "HATES", "Laziness"),
            ("ember", "LIKES", "Action"),
            ("ember", "LIKES", "Exercise"),
            ("ember", "HATES", "Laziness"),
            ("shadow", "LIKES", "Strategy"),
            ("shadow", "CARES_ABOUT", "Learning"),
        ]
        for npc_id, rel, concept in preferences:
            # MERGE relationship
            self.conn.execute(
                f"MATCH (n:NPC {{id: '{npc_id}'}}), (c:Concept {{name: '{concept}'}}) MERGE (n)-[:{rel}]->(c)"
            )

        # Default User
        self.conn.execute("MERGE (u:User {id: 'u_player'}) ON CREATE SET u.name = 'Player'")

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
            key_field = "id" if "id" in properties else "name"
            key_val = properties.get(key_field)

            # Prefer MERGE on key to avoid duplicate PK errors; SET the rest of the props
            if key_val:
                setters = ", ".join([f"n.{k} = '{v}'" for k, v in properties.items() if k != key_field])
                cypher = f"MERGE (n:{label} {{{key_field}: '{key_val}'}})"
                if setters:
                    cypher += f" SET {setters}"
            else:
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
        properties: Dict[str, Any] = None,
        from_key_field: str = "name",
        to_key_field: str = "name",
    ) -> bool:
        """
        Create a relationship between two nodes.

        Args:
            from_label: Label of the source node (e.g., 'User', 'Event')
            from_key: Value of the key field for the source node
            rel_type: Type of relationship (e.g., 'COMPLETED', 'TRIGGERED_BY')
            to_label: Label of the target node
            to_key: Value of the key field for the target node
            properties: Optional relationship properties
            from_key_field: Field to match for source node ('name' or 'id'), defaults to 'name'
            to_key_field: Field to match for target node ('name' or 'id'), defaults to 'name'
        """
        try:
            props_str = ""
            if properties:
                props_str = " {" + ", ".join([f"{k}: '{v}'" for k, v in properties.items()]) + "}"

            cypher = (
                f"MATCH (a:{from_label} {{{from_key_field}: '{from_key}'}}), "
                f"(b:{to_label} {{{to_key_field}: '{to_key}'}}) "
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
            # Query by name (since ID might correspond to name.lower())
            result = self.conn.execute(
                f"MATCH (n:NPC {{name: '{npc_name}'}}) RETURN n.name, n.role, n.mood, n.personality"
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

            if result.has_next():
                row = result.get_next()
                npc_data["name"] = row[0]
                npc_data["role"] = row[1]
                npc_data["mood"] = row[2]
                npc_data["personality"] = row[3] if len(row) > 3 else ""

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
            timestamp = int(datetime.now().timestamp())
            metadata_str = str(metadata).replace("'", "\\'")

            # Ensure user exists (ID)
            self.conn.execute(f"MERGE (u:User {{id: '{user_id}'}})")

            # Create event
            self.conn.execute(
                f"CREATE (e:Event {{id: '{event_id}', type: '{event_type}', "
                f"timestamp: {timestamp}, metadata: '{metadata_str}'}})"
            )

            # Link event to user
            self.conn.execute(
                f"MATCH (e:Event {{id: '{event_id}'}}), (u:User {{id: '{user_id}'}}) CREATE (e)-[:TRIGGERED_BY]->(u)"
            )

            return True
        except Exception as e:
            logger.error(f"Failed to record user event: {e}")
            return False

    def get_user_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent user events/interactions from graph"""
        try:
            result = self.conn.execute(
                f"MATCH (e:Event)-[:TRIGGERED_BY]->(u:User {{id: '{user_id}'}}) "
                f"RETURN e.id, e.type, e.timestamp, e.metadata "
                f"ORDER BY e.timestamp DESC LIMIT {limit}"
            )

            events = []
            while result.has_next():
                row = result.get_next()
                events.append({"id": row[0], "type": row[1], "timestamp": row[2], "metadata": row[3]})

            return events
        except Exception as e:
            logger.error(f"Failed to get user history: {e}")
            return []

    query_recent_context = get_user_history


_kuzu_instance = None


def get_kuzu_adapter() -> KuzuAdapter:
    global _kuzu_instance
    if _kuzu_instance is None:
        _kuzu_instance = KuzuAdapter()
    return _kuzu_instance
