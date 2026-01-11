import logging
import json
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select

from legacy.services.ai_engine import ai_engine
from application.services.context_service import context_service
from application.services.brain.flow_controller import flow_controller, FlowState

logger = logging.getLogger(__name__)


class AgentStatUpdate(BaseModel):
    stat_type: str = "VIT"  # STR, INT, VIT...
    xp_amount: int = 10
    hp_change: int = 0
    gold_change: int = 0


class AgentPlan(BaseModel):
    narrative: str
    stat_update: Optional[AgentStatUpdate] = None
    tool_calls: List[str] = Field(default_factory=list)  # e.g. ["update_quest:123", "add_item:potion"]
    flow_state: Dict[str, Any] = Field(default_factory=dict)  # Debug info about flow



class AgentSystemAction(BaseModel):
    action_type: str  # "DIFFICULTY_CHANGE", "PUSH_QUEST", "BRIDGE_GEN"
    details: Dict[str, Any]
    reason: str


class BrainService:
    """
    The Executive Function of the Cyborg.
    Orchestrates Context -> Flow -> AI -> Plan.
    """

    async def think(self, context: str = None, prompt: str = None, **kwargs) -> str:
        """
        Simple think method for PerceptionService.
        Returns raw LLM response as string.
        """
        if context is None:
            context = ""
        if prompt is None:
            prompt = "Respond to the event."

        system_prompt = f"""
你是 LifeOS 的遊戲敘事者。根據以下情境產生 JSON 回應。

情境:
{context}

回應格式 (JSON):
{{
  "narrative": "簡短的遊戲敘事 (繁體中文)",
  "actions": ["action1", "action2"]
}}
"""
        try:
            result = await ai_engine.generate_json(system_prompt, prompt)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Brain think failed: {e}")
            return json.dumps({"narrative": "系統思維中...", "actions": []}, ensure_ascii=False)

    async def think_with_session(self, session, user_id: str, user_text: str, pulsed_events: Dict = None) -> AgentPlan:
        # 1. Context
        memory = await context_service.get_working_memory(session, user_id)

        user_state = memory.get("user_state", {})

        # Inject Pulsed Events into memory/history context
        if pulsed_events:
            memory["pulsed_events"] = pulsed_events

        churn_risk = user_state.get("churn_risk", "LOW")

        # 2. Flow Physics (The "Thermostat")
        current_tier = "C"

        flow_target: FlowState = flow_controller.calculate_next_state(current_tier, [], churn_risk=churn_risk)

        # 3. System Prompt Engineering (The "Addiction Script")
        system_prompt = self._construct_system_prompt(memory, flow_target)

        # 4. AI Generation
        raw_plan = await ai_engine.generate_json(system_prompt, f"User Input: {user_text}")

        # 5. Hydrate & Validate
        try:
            if "stat_update" not in raw_plan:
                raw_plan["stat_update"] = None

            plan = AgentPlan(**raw_plan)
            plan.flow_state = {
                "tier": flow_target.difficulty_tier,
                "tone": flow_target.narrative_tone,
                "loot_mult": flow_target.loot_multiplier,
            }
            return plan

        except Exception as e:
            logger.error(f"Brain Parsing Failed: {e}. Raw: {raw_plan}")
            return AgentPlan(
                narrative="系統思維過載... (Fallback)",
                stat_update=AgentStatUpdate(xp_amount=5),
                flow_state={"error": str(e)},
            )

    def _construct_system_prompt(self, memory: Dict, flow: FlowState) -> str:
        # Construct Alert String
        alerts = ""
        pulsed = memory.get("pulsed_events", {})
        if pulsed.get("drain_amount", 0) > 0:
            alerts += f"\n⚠️ [SYSTEM ALERT] User was offline. HP Drained: {pulsed['drain_amount']}. Vitality Low."
        if pulsed.get("viper_taunt"):
            alerts += f"\n💀 [VIPER ALERT] Rival Taunt: '{pulsed['viper_taunt']}'."

        return f"""
Role: LifeOS-RPG Game Master (Addiction Engineered).
Language: Traditional Chinese (繁體中文).

# Context
User Level: {memory["user_state"].get("level")}
Time: {memory["time_context"]}
Recent Log:
{memory["short_term_history"]}

# Graph Memory (Knowledge)
{json.dumps(memory.get("long_term_context", []), ensure_ascii=False)}

# Real-Time Alerts (MUST ACKNOWLEDGE)
{alerts}

# Operational Directive (Flow State)
Target Difficulty: {flow.difficulty_tier}
Narrative Tone: {flow.narrative_tone.upper()} (Strictly adhere to this!)
Loot Multiplier: {flow.loot_multiplier}x
Churn Risk: {memory["user_state"].get("churn_risk")}

# Goal
Analyze the user's input. If it is a valid action, reward them based on Flow State.
If alerts exist, scold/warn them about inactivity.
If they are failing/tired, encourage them (Lower Difficulty).
If they are bored/winning, challenge them (Higher Difficulty).

# Output Schema (JSON)
{{
  "narrative": "Immersive response < 100 chars. Tone: {flow.narrative_tone}",
  "stat_update": {{
      "stat_type": "STR|INT|VIT|WIS|CHA",
      "xp_amount": 10-100 (Scale with Difficulty {flow.difficulty_tier}),
      "hp_change": int (negative for damage, positive for heal),
      "gold_change": int
  }},
  "tool_calls": ["start_quest", "complete_quest"] (Optional list)
}}
"""

    async def execute_system_judgment(self, session, user_id: str) -> Optional[AgentSystemAction]:
        """
        The Autonomous Executive Loop.
        Analyzes performance metrics and decides on system-level interventions.
        Does NOT generate text. It generates RULES.
        """
        from legacy.services.quest_service import quest_service
        from legacy.models.quest import Quest, QuestStatus, Goal, GoalStatus

        # 1. Gather Metrics (Last 3 Days)
        # Using a simple heuristic for now: Active Quests Age
        # In future, use CompletionRateService
        stmt = select(Quest).where(
            Quest.user_id == user_id, Quest.status == QuestStatus.ACTIVE.value
        )
        active_quests = (await session.execute(stmt)).scalars().all()

        fail_streak = 0
        oldest_active = 0
        now = datetime.datetime.now()
        
        # Check staleness
        for q in active_quests:
            if q.created_at: 
                # Handle naive vs aware datetime
                created = q.created_at
                if created.tzinfo:
                   created = created.replace(tzinfo=None)
                age = (now - created).days
                if age > 2:
                    fail_streak += 1
                oldest_active = max(oldest_active, age)

        # 2. Judge (The Algorithm)
        if fail_streak >= 2:
            # POLICY: OVERWHELM DETECTED
            logger.info(f"Executive Judgment: User {user_id} is overwhelmed. Downgrading difficulty.")
            count = await quest_service.bulk_adjust_difficulty(session, user_id, target_tier="E")
            return AgentSystemAction(
                action_type="DIFFICULTY_CHANGE", 
                details={"tier": "E", "count": count},
                reason="Overwhelm Detected (Stale Quests)"
            )
        
        # 3. Momentum Check (Last Active)
        if not active_quests:
             pass

        # 4. Goal Stagnation Check (The Bridge)
        # Find Active Goals where no Quest was created in > 7 days
        stmt = select(Goal).where(Goal.user_id == user_id, Goal.status == GoalStatus.ACTIVE.value)
        active_goals = (await session.execute(stmt)).scalars().all()
        
        for goal in active_goals:
            # Check most recent quest
            q_stmt = select(Quest).where(
                Quest.goal_id == goal.id
            ).order_by(Quest.created_at.desc()).limit(1)
            last_quest = (await session.execute(q_stmt)).scalars().first()
            
            days_since = 999
            if last_quest and last_quest.created_at:
                 created = last_quest.created_at
                 if created.tzinfo: created = created.replace(tzinfo=None)
                 days_since = (now - created).days
            elif goal.created_at:
                 created = goal.created_at
                 if created.tzinfo: created = created.replace(tzinfo=None)
                 days_since = (now - created).days
            
            if days_since > 30:
                 # POLICY: CHECKMATE PROTOCOL (Forced Accountability)
                 logger.warning(f"Executive Judgment: Goal {goal.title} ignored for {days_since}d. TRIGGERING CHECKMATE.")
                 # Force Boss Fight logic could go here, or just a very severe Bridge Quest
                 # Simple version: Priority S bridge quest
                 return AgentSystemAction(
                    action_type="PUSH_QUEST",
                    details={"title": f"BOSS: Reclaim {goal.title}", "diff": "S", "type": "REDEMPTION"},
                    reason=f"CHECKMATE (Goal ignored {days_since} days)"
                 )
            
            if days_since > 7:
                 # POLICY: STAGNATION DETECTED
                 logger.info(f"Executive Judgment: Goal {goal.title} is stagnant ({days_since}d). Building Bridge.")
                 bridge_quest = await quest_service.create_bridge_quest(session, user_id, goal.id)
                 if bridge_quest:
                     return AgentSystemAction(
                        action_type="BRIDGE_GEN",
                        details={"quest_title": bridge_quest.title, "goal": goal.title},
                        reason=f"Goal Stagnation ({days_since} days)"
                     )

        # 5. Reality Sync (Stub)
        # Check external calendar load
        external_load = await self._get_external_load(user_id)
        if external_load > 0.8: # > 80% busy
             logger.info("Executive Judgment: External High Load detected. Adjusting difficulty.")
             count = await quest_service.bulk_adjust_difficulty(session, user_id, target_tier="E")
             return AgentSystemAction(
                action_type="DIFFICULTY_CHANGE",
                details={"tier": "E", "source": "CALENDAR_SYNC"},
                reason="High External Load"
             )

        return None

    async def _get_external_load(self, user_id: str) -> float:
        """Stub for Google/Outlook Calendar integration."""
        return 0.0


brain_service = BrainService()

