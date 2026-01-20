import logging
import json
from typing import Dict, Any, List, Optional
from application.services.ai_engine import ai_engine
from application.services.context_service import context_service
from application.services.brain.flow_controller import flow_controller, FlowState
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentStatUpdate(BaseModel):
    stat_type: str = "VIT"
    xp_amount: int = 10
    hp_change: int = 0
    gold_change: int = 0


class AgentPlan(BaseModel):
    narrative: str
    stat_update: Optional[AgentStatUpdate] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    flow_state: Dict[str, Any] = Field(default_factory=dict)


class NarratorService:
    """
    Handles Narrative Generation, Prompt Construction, and Intent Classification.
    """

    async def think(self, context: str = None, prompt: str = None, **kwargs) -> str:
        """Simple think method for PerceptionService."""
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
            logger.error(f"Narrator think failed: {e}")
            return json.dumps({"narrative": "系統思維中...", "actions": []}, ensure_ascii=False)

    async def think_with_session(self, session, user_id: str, user_text: str, pulsed_events: Dict = None) -> AgentPlan:
        # 1. Context
        memory = await context_service.get_working_memory(session, user_id)
        user_state = memory.get("user_state", {})

        # Inject Pulsed Events
        if pulsed_events:
            memory["pulsed_events"] = pulsed_events

        churn_risk = user_state.get("churn_risk", "LOW")

        # Enrich context with Graph history
        try:
            from app.core.container import container

            # Use container instead of direct import
            if container and container.graph_service:
                # Note: graph_service return dict objects for updates, but maybe objects for get_user_history?
                # application/services/graph_service.py: get_user_history returns List[Dict] usually.
                # Let's verify return type of get_user_history.
                # It calls adapter.query -> returns rows -> adapter.get_user_history usually returns list of dicts.
                # We assume list of dicts.
                graph_history = await container.graph_service.get_user_history(user_id, limit=5)
                recent_actions = []
                for event in graph_history:
                    if event.get("event_type") == "AI_TOOL_CALL":
                        meta = event.get("metadata", {})
                        recent_actions.append(f"[TOOL] {meta.get('tool')}: {meta.get('title', 'N/A')}")
                if recent_actions:
                    memory["recent_ai_actions"] = recent_actions
        except Exception as e:
            logger.warning(f"Graph context enrichment failed: {e}")

        # 2. Flow Physics
        current_tier = user_state.get("current_tier", "C")
        recent_performance = []  # TODO: Implement performance fetching

        # Fetch PID State (Feature 2)
        from sqlalchemy import select
        from app.models.gamification import UserPIDState

        try:
            stmt = select(UserPIDState).where(UserPIDState.user_id == user_id)
            pid_res = await session.execute(stmt)
            pid_state = pid_res.scalars().first()

            if not pid_state:
                from sqlalchemy.exc import IntegrityError
                try:
                    # Use nested transaction (savepoint) to handle race condition
                    async with session.begin_nested():
                        pid_state = UserPIDState(user_id=user_id)
                        session.add(pid_state)
                        await session.flush()
                except IntegrityError:
                    # Race condition hit: someone else created it. Fetch again.
                    logger.info(f"Race condition detected for PID state user {user_id[-6:]}, refetching.")
                    pid_res = await session.execute(stmt)
                    pid_state = pid_res.scalars().first()
        except Exception as e:
            logger.warning(f"Failed to fetch/create PID state: {e}")
            pid_state = None

        flow_target: FlowState = flow_controller.calculate_next_state(
            current_tier, recent_performance, churn_risk=churn_risk, pid_state=pid_state
        )

        # 3. System Prompt
        intent_hint = self._classify_intent(user_text)
        system_prompt = self._construct_system_prompt(memory, flow_target, intent_hint=intent_hint)

        raw_plan = {}
        try:
            # 4. AI Generation
            raw_plan = await ai_engine.generate_json(system_prompt, f"User Input: {user_text}")

            logger.info(f"AI Raw Response: {json.dumps(raw_plan, ensure_ascii=False)[:500]}")
            if raw_plan.get("tool_calls"):
                logger.info(f"AI Tool Calls Detected: {raw_plan['tool_calls']}")

            # 5. Hydrate & Validate
            if "stat_update" not in raw_plan:
                raw_plan["stat_update"] = None

            plan = AgentPlan(**raw_plan)

            # === FEATURE 1: Tool Forcing Layer ===
            # If intent requires tool but AI didn't return one, force inject
            if intent_hint == "CREATE_GOAL" and not plan.tool_calls:
                goal_title = self._extract_goal_title(user_text)
                plan.tool_calls = [{"tool": "create_goal", "args": {"title": goal_title, "category": "general"}}]
                plan.narrative = f"🎯 目標設定中：{goal_title}"
                logger.info(f"Tool Forcing: Injected create_goal for '{goal_title}'")
            elif intent_hint == "START_CHALLENGE" and not plan.tool_calls:
                challenge_title = self._extract_goal_title(user_text)
                plan.tool_calls = [{"tool": "start_challenge", "args": {"title": challenge_title, "difficulty": "D"}}]
                plan.narrative = f"⚔️ 挑戰確認：{challenge_title}"
                logger.info(f"Tool Forcing: Injected start_challenge for '{challenge_title}'")

            # Post-process
            if plan.narrative:
                plan.narrative = plan.narrative.replace("[無操作]", "").replace("[ 無操作]", "").strip()
                plan.narrative = plan.narrative.replace("。。", "。").strip()
                if len(plan.narrative) > 80:
                    plan.narrative = plan.narrative[:77] + "..."
                if not plan.narrative:
                    plan.narrative = "🤔 有什麼需要幫忙的嗎？"

            plan.flow_state = {
                "tier": flow_target.difficulty_tier,
                "tone": flow_target.narrative_tone,
                "loot_mult": flow_target.loot_multiplier,
            }
            return plan

        except Exception as e:
            logger.error(f"Brain Parsing Failed: {e}. Raw: {raw_plan}")
            return AgentPlan(
                narrative="Cipher Interference... re-calibrating protocols. (System Fallback)",
                stat_update=AgentStatUpdate(xp_amount=5),
                flow_state={"error": str(e)},
            )

    def _classify_intent(self, text: str) -> str:
        text = text.lower()
        if any(w in text for w in ["想要", "我要", "想成為", "想學", "目標", "new goal", "i want"]):
            return "CREATE_GOAL"
        if any(w in text for w in ["挑戰", "試試", "開始", "start", "challenge"]):
            return "START_CHALLENGE"
        if any(w in text for w in ["你好", "嗨", "hello", "hi", "早安", "晚安"]):
            return "GREETING"
        return "UNKNOWN"

    def _extract_goal_title(self, text: str) -> str:
        """Extract goal title from user input by removing common prefixes."""
        import re

        # Remove common prefixes
        prefixes = [
            r"^我想要?",
            r"^我要",
            r"^想要?",
            r"^想成為",
            r"^想學[習會]?",
            r"^目標是?",
            r"^新目標[：:]",
            r"^i want to",
            r"^i want",
            r"^開始",
            r"^挑戰",
            r"^試試",
        ]
        cleaned = text.strip()
        for prefix in prefixes:
            cleaned = re.sub(prefix, "", cleaned, flags=re.IGNORECASE).strip()
        # Fallback if nothing left
        if not cleaned:
            cleaned = text.strip()
        # Limit length
        if len(cleaned) > 50:
            cleaned = cleaned[:47] + "..."
        return cleaned

    def _construct_system_prompt(self, memory: Dict, flow: FlowState, intent_hint: str = "UNKNOWN") -> str:
        alerts = ""
        pulsed = memory.get("pulsed_events", {})
        if pulsed.get("drain_amount", 0) > 0:
            alerts += f"\n⚠️ [SYSTEM ALERT] User was offline. HP Drained: {pulsed['drain_amount']}. Vitality Low."
        if pulsed.get("viper_taunt"):
            alerts += f"\n💀 [VIPER ALERT] Rival Taunt: '{pulsed['viper_taunt']}'."

        intent_instruction = ""
        if intent_hint == "CREATE_GOAL":
            intent_instruction = "\n👉 SYSTEM HINT: User likely wants to set a GOAL. USE `create_goal` tool."
        elif intent_hint == "START_CHALLENGE":
            intent_instruction = "\n👉 SYSTEM HINT: User wants to start a challenge. USE `start_challenge` tool."

        identity_ctx = memory.get("identity_context", {}) or {}
        identity_title = identity_ctx.get("title", "The Socratic Architect")
        identity_values = ", ".join(identity_ctx.get("core_values", [])) or "Growth, Autonomy"
        identity_tags = ", ".join(identity_ctx.get("identity_tags", [])) or "Seeker, Architect"

        long_term_context = memory.get("long_term_context", [])
        try:
            long_term_json = json.dumps(long_term_context, ensure_ascii=False)
        except TypeError:
            long_term_json = json.dumps([str(long_term_context)], ensure_ascii=False)

        return f"""
Role: Grounded Performance Coach (LifeOS AI).
Language: Traditional Chinese (繁體中文).
Core Directive: ACT. Do not just speak.
Use 'tool_calls' to modify Game State.

# Context
User Level: {memory["user_state"].get("level")}
Time: {memory["time_context"]}
Churn Risk: {memory["user_state"].get("churn_risk")}

# Recent History
{memory["short_term_history"]}

# Graph Memory (Deep Context)
{long_term_json}

# Recent AI Actions
{chr(10).join(memory.get("recent_ai_actions", ["No recent AI actions"]))}

# Identity Context
Identity: {identity_title}
Core Values: {identity_values}
Identity Tags: {identity_tags}

# Operational Directive
Difficulty: {flow.difficulty_tier} | Tone: {flow.narrative_tone.upper()} | Loot: {flow.loot_multiplier}x

# ALERTS
{alerts}

# SYSTEM GUIDANCE
Detected Intent: {intent_hint} {intent_instruction}

# STRICT OUTPUT RULES
1. **EMOJI FIRST**: Start with ONE emoji.
2. **SHORT**: Narrative < 60 chars.
3. **TOOL USE**: If intent is CREATE_GOAL or START_CHALLENGE, you MUST use the tool.
4. **NO FLUFF**: Don't say "你想先做什麼", "一步一步".
5. **DEFAULT**: If unsure, assume the user is reporting progress or asking for guidance.

# TOOL SCHEMAS
1. `create_goal`: args: {{ "title": "str", "category": "health|career|learning", "deadline": "YYYY-MM-DD" }}
2. `start_challenge`: args: {{ "title": "str", "difficulty": "E|D|C", "type": "MAIN|SIDE" }}

# OUTPUT SCHEMA (JSON)
{{
  "narrative": "Emoji + Short response",
  "stat_update": {{ "stat_type": "VIT", "xp_amount": 10, "hp_change": 0, "gold_change": 0 }},
  "tool_calls": []
}}
"""
