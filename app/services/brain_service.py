import logging
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from legacy.services.ai_engine import ai_engine
from app.services.context_service import context_service
from app.services.brain.flow_controller import flow_controller, FlowState

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

    async def think(self, 
                    user_id: str, 
                    user_text: str, 
                    recent_performance: List[bool] = None) -> AgentPlan:
        
        # 0. Defaults
        if recent_performance is None:
            recent_performance = [] # Need to fetch from context or passed in

        # 1. Gather Context (Hippocampus)
        # We need session? For now ContextService assumes session dependency or manage it?
        # ContextService.get_working_memory needs SESSION.
        # So think() must likely accept session.
        # I will update signature to optionally take memory dict OR I refactor integration.
        # For now, let's assume caller (GameLoop) passes session.
        # Wait, the signature in GameLoop...
        # Let's keep `think` high level. `GameLoop` should call `context_service` first?
        # Or `think` accepts session.
        # Let's make `think` accept `context_data` (Dict) to remain pure, 
        # OR accept `session`. Accepting `session` is easier for orchestration.
        pass 

    async def think_with_session(self, session, user_id: str, user_text: str) -> AgentPlan:
        
        # 1. Context
        memory = await context_service.get_working_memory(session, user_id)
        
        user_state = memory.get("user_state", {})
        # Extract performance from ActionLogs in memory?
        # Heuristic: "B" or higher in log = Success?
        # For now, let's just assume empty performance history for PID if not readily available, 
        # or parse `short_term_history`? 
        # Let's use `user_state.get("streak")` as a proxy for success? No.
        # Future: Store success/fail explicitly. For now empty list (neutral flow).
        
        performance_proxy = [] # TODO: Extract from logs
        churn_risk = user_state.get("churn_risk", "LOW")
        
        # 2. Flow Physics (The "Thermostat")
        # Current tier?
        # We don't track current tier in User model strictly, log has it.
        # Assume "C" default.
        current_tier = "C" 
        
        flow_target: FlowState = flow_controller.calculate_next_state(
            current_tier, 
            performance_proxy, 
            churn_risk=churn_risk
        )
        
        # 3. System Prompt Engineering (The "Addiction Script")
        system_prompt = self._construct_system_prompt(memory, flow_target)
        
        # 4. AI Generation
        raw_plan = await ai_engine.generate_json(system_prompt, f"User Input: {user_text}")
        
        # 5. Hydrate & Validate
        try:
            # Handle nested logic if AI returns simplified structure
            # Ensure stat_update is properly formatted
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
            # Fallback plan
            return AgentPlan(
                narrative="系統思維過載... (Fallback)",
                stat_update=AgentStatUpdate(xp_amount=5),
                flow_state={"error": str(e)}
            )

    def _construct_system_prompt(self, memory: Dict, flow: FlowState) -> str:
        return f"""
Role: LifeOS-RPG Game Master (Addiction Engineered).
Language: Traditional Chinese (繁體中文).

# Context
User Level: {memory['user_state'].get('level')}
Time: {memory['time_context']}
Recent Log:
{memory['short_term_history']}

# Graph Memory (Knowledge)
{json.dumps(memory.get('long_term_context', []), ensure_ascii=False)}

# Operational Directive (Flow State)
Target Difficulty: {flow.difficulty_tier}
Narrative Tone: {flow.narrative_tone.upper()} (Strictly adhere to this!)
Loot Multiplier: {flow.loot_multiplier}x
Churn Risk: {memory['user_state'].get('churn_risk')}

# Goal
Analyze the user's input. If it is a valid action, reward them based on Flow State.
If they are failing/tired, encourage them (Lower Difficulty).
If they are bored/winning, challenge them (Higher Difficulty).

# Output Schema (JSON)
{{
  "narrative": "Immersive response < 60 chars. Tone: {flow.narrative_tone}",
  "stat_update": {{
      "stat_type": "STR|INT|VIT|WIS|CHA",
      "xp_amount": 10-100 (Scale with Difficulty {flow.difficulty_tier}),
      "hp_change": int (negative for damage, positive for heal),
      "gold_change": int
  }},
  "tool_calls": ["start_quest", "complete_quest"] (Optional list)
}}
"""

brain_service = BrainService()
