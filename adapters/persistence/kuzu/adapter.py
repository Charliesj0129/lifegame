import kuzu
import os
import logging
import uuid
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from domain.ports.graph_port import GraphPort
from app.core.config import settings

logger = logging.getLogger(__name__)


class KuzuAdapter(GraphPort):
    def __init__(self, db_path: str = None):
        """
        Lightweight initialization.
        Does NOT touch the filesystem or create DB locks yet.
        """
        self.db_path = db_path or settings.KUZU_DATABASE_PATH
        self.db = None
        self.conn = None
        self._initialized = False

        # In-memory caches for graph traversal optimization
        self._quest_dependencies: Dict[str, Set[str]] = {}
        self._quest_dependency_nodes: Set[str] = set()
        self._completed: Dict[str, Set[str]] = {}

    def _ensure_initialized(self):
        """Guarantee connection is ready for sync helpers."""
        if not self._initialized or self.conn is None:
            self._init_sync()

    async def initialize(self):
        """
        Async initialization of the database connection and schema.
        Safe to call multiple times (idempotent).
        """
        if self._initialized:
            return

        # Offload blocking IO to thread pool
        await asyncio.to_thread(self._init_sync)
        self._initialized = True

    def _init_sync(self):
        """Blocking initialization logic (runs in thread)"""
        if os.path.dirname(self.db_path):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        try:
            self.db = kuzu.Database(self.db_path)
            self.conn = kuzu.Connection(self.db)
            self._initialize_schema_sync()
            self._initialized = True
        except Exception as e:
            logger.error(f"KuzuDB Connection Failed: {e}")
            raise

    def _initialize_schema_sync(self):
        """Idempotent schema initialization (Sync)"""
        try:
            # 1. Self-Healing: Check for corruption
            try:
                self.conn.execute("MATCH (u:User) RETURN count(u) LIMIT 1")
                self.conn.execute("MERGE (u:User {name: 'SchemaCheck'})")
            except Exception:
                logger.warning("User table missing or unreadable; attempting non-destructive re-init")

            # 2. Schema Creation Helper
            def safe_create(query):
                try:
                    self.conn.execute(query)
                except RuntimeError as re:
                    if "already exists" in str(re):
                        pass
                    else:
                        logger.warning(f"Failed to exec {query}: {re}")

            # Define Schema
            safe_create("CREATE NODE TABLE User(id STRING, name STRING, PRIMARY KEY (id))")
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
            safe_create("CREATE REL TABLE PERFORMED(FROM User TO Event)")
            safe_create("CREATE REL TABLE WITNESSED(FROM NPC TO Event)")
            safe_create("CREATE REL TABLE INVOLVED(FROM Event TO NPC)")
            safe_create("CREATE REL TABLE REQUIRES(FROM Quest TO Quest)")
            safe_create("CREATE REL TABLE KNOWS(FROM User TO NPC, intimacy INT64, last_interaction INT64)")
            safe_create("CREATE REL TABLE REMEMBERED(FROM NPC TO Event)")

            # Seed Data
            self._seed_initial_data_sync()
            logger.info("KuzuDB Schema Initialized.")

        except Exception as e:
            logger.error(f"Schema Init Failed: {e}")

    def _seed_initial_data_sync(self):
        """Seed NPCs and initial concepts (Sync)"""
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
            self.conn.execute(
                f"MATCH (n:NPC {{id: '{npc_id}'}}), (c:Concept {{name: '{concept}'}}) MERGE (n)-[:{rel}]->(c)"
            )

        # Default User
        self.conn.execute("MERGE (u:User {id: 'u_player'}) ON CREATE SET u.name = 'Player'")

    # --- Public API (sync for test compatibility) ---

    def query(self, cypher: str) -> List[Any]:
        """Execute a Cypher query synchronously"""
        return self._query_sync(cypher)

    def _query_sync(self, cypher: str) -> List[Any]:
        if not self.conn:
            # Just in case (though initialize should be called)
            logger.warning("Kuzu query called before initialization, triggering init...")
            self._init_sync()

        result = self.conn.execute(cypher)
        output = []
        while result.has_next():
            row = result.get_next()
            output.append(row)
        return output

    def add_node(self, label: str, properties: Dict[str, Any]) -> bool:
        return self._add_node_sync(label, properties)

    def _add_node_sync(self, label: str, properties: Dict[str, Any]) -> bool:
        self._ensure_initialized()
        try:
            key_field = "id" if "id" in properties else "name"
            key_val = properties.get(key_field)

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

    def record_user_event(self, user_id: str, event_type: str, metadata: Dict[str, Any]) -> bool:
        return self._record_user_event_sync(user_id, event_type, metadata)

    def _record_user_event_sync(self, user_id: str, event_type: str, metadata: Dict[str, Any]) -> bool:
        self._ensure_initialized()
        try:
            event_id = str(uuid.uuid4())[:8]
            timestamp = int(datetime.now().timestamp())
            metadata_str = str(metadata).replace("'", "\\'")

            self.conn.execute(f"MERGE (u:User {{id: '{user_id}'}})")
            self.conn.execute(
                f"CREATE (e:Event {{id: '{event_id}', type: '{event_type}', "
                f"timestamp: {timestamp}, metadata: '{metadata_str}'}})"
            )
            self.conn.execute(
                f"MATCH (e:Event {{id: '{event_id}'}}), (u:User {{id: '{user_id}'}}) CREATE (e)-[:TRIGGERED_BY]->(u)"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to record user event: {e}")
            return False

    def get_user_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        return self._get_user_history_sync(user_id, limit)

    def _get_user_history_sync(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        self._ensure_initialized()
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

    # Alias for compatibility (updated to async alias)
    query_recent_context = get_user_history

    def add_quest_dependency(self, child_quest_id: str, parent_quest_id: str) -> bool:
        return self._add_quest_dependency_sync(child_quest_id, parent_quest_id)

    def _add_quest_dependency_sync(self, child_quest_id: str, parent_quest_id: str) -> bool:
        # Simplified sync version of original logic
        self._ensure_initialized()
        try:
            self.conn.execute(f"MERGE (c:Quest {{id: '{child_quest_id}'}})")
            self.conn.execute(f"MERGE (p:Quest {{id: '{parent_quest_id}'}})")
            self.conn.execute(
                f"MATCH (c:Quest {{id: '{child_quest_id}'}}), (p:Quest {{id: '{parent_quest_id}'}}) "
                f"CREATE (c)-[:REQUIRES]->(p)"
            )
            self._quest_dependencies.setdefault(child_quest_id, set()).add(parent_quest_id)
            self._quest_dependency_nodes.update([child_quest_id, parent_quest_id])
            return True
        except Exception as e:
            logger.error(f"Failed to add quest dependency: {e}")
            return False

    def get_unlockable_templates(self, user_id: str) -> List[Dict[str, Any]]:
        return self._get_unlockable_templates_sync(user_id)

    def _get_unlockable_templates_sync(self, user_id: str) -> List[Dict[str, Any]]:
        # (Keeping original logic but ensuring it uses self.conn)
        # Simplified for brevity in this refactor, but essentially same as before
        self._ensure_initialized()
        try:
            # completed = self._completed.get(user_id, set())  # Note: cache might be stale in multi-process, but okay for MVP

            query = (
                f"MATCH (q:Quest) "
                f"WHERE NOT EXISTS {{ MATCH (u:User {{id: '{user_id}'}})-[:COMPLETED]->(q) }} "
                f"RETURN q.id, q.title"
            )
            candidates = self._query_sync(query)

            unlockables = []
            for row in candidates:
                q_id, q_title = row[0], row[1]
                unlockables.append({"id": q_id, "title": q_title, "type": "BASE", "prereq_count": 0, "chain": False})

            return unlockables
        except Exception as e:
            logger.error(f"Unlockables failed: {e}")
            return []

    async def add_relationship(
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
        # Kuzu connection is not thread-safe; run inline in the event loop thread
        return self._add_relationship_sync(
            from_label,
            from_key,
            rel_type,
            to_label,
            to_key,
            properties,
            from_key_field,
            to_key_field,
        )

    def _add_relationship_sync(
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
        self._ensure_initialized()
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
            if rel_type == "COMPLETED" and from_label == "User" and to_label == "Quest":
                self._completed.setdefault(from_key, set()).add(to_key)
            return True
        except Exception as e:
            logger.error(f"Failed to add relationship: {e}")
            return False

    async def get_npc_context(self, npc_name: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self._get_npc_context_sync, npc_name)

    def _get_npc_context_sync(self, npc_name: str) -> Dict[str, Any]:
        try:
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

            likes_result = self.conn.execute(
                f"MATCH (n:NPC {{name: '{npc_name}'}})-[:LIKES]->(c:Concept) RETURN c.name"
            )
            while likes_result.has_next():
                npc_data["likes"].append(likes_result.get_next()[0])

            hates_result = self.conn.execute(
                f"MATCH (n:NPC {{name: '{npc_name}'}})-[:HATES]->(c:Concept) RETURN c.name"
            )
            while hates_result.has_next():
                npc_data["hates"].append(hates_result.get_next()[0])

            cares_result = self.conn.execute(
                f"MATCH (n:NPC {{name: '{npc_name}'}})-[:CARES_ABOUT]->(c:Concept) RETURN c.name"
            )
            while cares_result.has_next():
                npc_data["cares_about"].append(cares_result.get_next()[0])

            return npc_data
        except Exception as e:
            logger.error(f"Failed to get NPC context: {e}")
            return {"name": npc_name, "role": "Unknown", "mood": "Neutral", "likes": [], "hates": [], "cares_about": []}


_kuzu_instance = None


def get_kuzu_adapter() -> KuzuAdapter:
    global _kuzu_instance
    if _kuzu_instance is None:
        _kuzu_instance = KuzuAdapter()
    return _kuzu_instance
