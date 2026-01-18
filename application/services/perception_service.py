import json
import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from domain.ports.perception_port import PerceptionPort
from domain.events.game_event import GameEvent
from domain.models.game_result import GameResult
from app.core.container import container
from application.services.vector_service import vector_service
from application.services.brain_service import brain_service
from application.services.action_service import action_service

logger = logging.getLogger(__name__)


class PerceptionService(PerceptionPort):
    def __init__(self):
        # Dependencies (Services)
        # Ideally these are injected, but using singletons for now
        self.graph = container.graph_service
        self.vector = vector_service
        self.brain = brain_service
        self.actions = action_service

    async def analyze_visual_context(
        self, image_bytes: bytes, user_id: str, db_session: AsyncSession | None = None
    ) -> Dict[str, Any]:
        """
        The Cortex Loop:
        1. Query Graph (Who cares?)
        2. Query Vector (Context/Memory)
        3. Brain Think (Narrative + Decision)
        """
        pass  # Placeholder for implementation

    async def process_event(self, event: GameEvent, db_session: AsyncSession = None) -> GameResult:
        """
        The Cortex Loop:
        1. Query Graph (Who cares?)
        2. Query Vector (Context/Memory)
        3. Brain Think (Narrative + Decision)
        4. Execute Actions
        """
        logger.info(f"Processing Event: {event.type} from {event.source}")

        # 1. Graph Query
        npcs = await self._query_interested_npcs(event)

        # 2. Vector Recall
        memory_context = await self._recall_memories(event)

        # 3. Brain Think
        narrative_context = f"Event: {event.type}. Metadata: {event.metadata}. Memory: {memory_context}"
        npc_name = npcs[0] if npcs else "System"

        llm_response = await self.brain.think(
            context=narrative_context,
            prompt=f"Narrate this event as if the NPC '{npc_name}' is observing it. Decide consequences.",
        )

        brain_output = self._parse_brain_response(llm_response)

        # 4. Execute Actions (Side Effects)
        executed_actions = []
        if db_session:
            executed_actions = await self.actions.execute_actions(brain_output.get("actions", []), db_session)

        # Return Result
        return GameResult(
            text=brain_output.get("narrative", ""),
            metadata={"actions_taken": executed_actions, "npcs_involved": npcs, "source_event_id": event.id},
        )

    async def _query_interested_npcs(self, event: GameEvent) -> List[str]:
        # Minimal Logic: Just get all NPCs for now or filter by event type relation if we had it
        # Future: MATCH (n:NPC)-[:CARES_ABOUT]->(e:EventType {name: event.type})
        try:
            # Using cursor wrapper from GraphService
            # GraphPort.query returns List[Any] (rows), not a cursor
            result_rows = await self.graph.query("MATCH (n:NPC) RETURN n.name, n.role")
            npcs = []
            for row in result_rows:
                if row:
                    npcs.append(f"{row[0]} ({row[1]})")
            return npcs
        except Exception as e:
            logger.error(f"Graph Query Failed: {e}")
            return []

    async def _recall_memories(self, event: GameEvent) -> str:
        query_text = f"{event.type} {event.metadata}"
        memories = await self.vector.search_memories(query_text)
        return str(memories) if memories else "No relevant memories."

    def _parse_brain_response(self, text: str) -> Dict[str, Any]:
        try:
            clean_json = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except json.JSONDecodeError:
            return {"narrative": text, "actions": []}


perception_service = PerceptionService()
