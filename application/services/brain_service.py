import logging
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from legacy.services.ai_engine import ai_engine
from application.services.context_service import context_service
from application.services.brain.flow_controller import flow_controller, FlowState

logger = logging.getLogger(__name__)

class AgentStatUpdate(BaseModel):
    stat_type: str = "VIT" # STR, INT, VIT...
    xp_amount: int = 10
    hp_change: int = 0
    gold_change: int = 0

class AgentPlan(BaseModel):
    narrative: str
    stat_update: Optional[AgentStatUpdate] = None
    tool_calls: List[str] = Field(default_factory=list) # e.g. ["update_quest:123", "add_item:potion"]
    flow_state: Dict[str, Any] = Field(default_factory=dict) # Debug info about flow

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
        # Fetch real tier from user state or default to C
        current_tier = user_state.get("current_tier", "C")
        
        # TODO: Parse recent_performance from short_term_history or add to ContextService
        recent_performance = [] 

        flow_target: FlowState = flow_controller.calculate_next_state(
            current_tier, 
            recent_performance, 
            churn_risk=churn_risk
        )
        
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
                "loot_mult": flow_target.loot_multiplier
            }
            return plan
            
        except Exception as e:
            logger.error(f"Brain Parsing Failed: {e}. Raw: {raw_plan}")
            return AgentPlan(
                narrative="Cipher Interference... re-calibrating protocols. (System Fallback)",
                stat_update=AgentStatUpdate(xp_amount=5),
                flow_state={"error": str(e)}
            )

    def _construct_system_prompt(self, memory: Dict, flow: FlowState) -> str:
        # Construct Alert String
        alerts = ""
        pulsed = memory.get("pulsed_events", {})
        if pulsed.get("drain_amount", 0) > 0:
            alerts += f"\n⚠️ [SYSTEM ALERT] User was offline. HP Drained: {pulsed['drain_amount']}. Vitality Low."
        if pulsed.get("viper_taunt"):
            alerts += f"\n💀 [VIPER ALERT] Rival Taunt: '{pulsed['viper_taunt']}'."

        # Identity Injection
        identity = memory.get("identity_context", {})
        values = ", ".join(identity.get("core_values", []))
        self_perception = ", ".join(identity.get("identity_tags", []))

        return f"""
Role: The Socratic Architect (LifeOS AI).
Language: Traditional Chinese (繁體中文).
Core Directive: You are NOT a generic chatbot. You are the user's "External Prefrontal Cortex".
Your goal is to align their actions with their VALUES ({values}) and IDENTITY ({self_perception}).

# Context
User Level: {memory['user_state'].get('level')}
Time: {memory['time_context']}
Churn Risk: {memory['user_state'].get('churn_risk')}

# Recent History
{memory['short_term_history']}

# Graph Memory (Deep Context)
{json.dumps(memory.get('long_term_context', []), ensure_ascii=False)}

# Operational Directive (Flow State)
Target Difficulty: {flow.difficulty_tier}
Narrative Tone: {flow.narrative_tone.upper()}
Loot Multiplier: {flow.loot_multiplier}x

# ALERTS
{alerts}

# INSTRUCTIONS
1. Analyze User Input.
2. If they are setting a goal, use SOCRATIC QUESTIONING to deepen it. (e.g. "Why 800? What does that unlock for you?")
3. If they are failing, be Encouraging (Tone: {flow.narrative_tone}).
4. If they are bored, be Challenging.
5. NEVER be abusive unless 'Viper' mode is explicitly active. Be Constructive.

# Output Schema (JSON)
{{
  "narrative": "Immersive response < 120 chars. Tone: {flow.narrative_tone}",
  "stat_update": {{
      "stat_type": "STR|INT|VIT|WIS|CHA",
      "xp_amount": 10-100,
      "hp_change": int,
      "gold_change": int
  }},
  "tool_calls": ["start_quest", "complete_quest"]
}}
"""

brain_service = BrainService()
