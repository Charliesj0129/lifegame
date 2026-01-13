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
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)  # [{"tool": "name", "args": {}}]
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
        # Fetch real tier from user state or default to C
        current_tier = user_state.get("current_tier", "C")

        # TODO: Parse recent_performance from short_term_history or add to ContextService
        recent_performance = []

        flow_target: FlowState = flow_controller.calculate_next_state(
            current_tier, recent_performance, churn_risk=churn_risk
        )

        # 3. System Prompt Engineering (The "Addiction Script")
        system_prompt = self._construct_system_prompt(memory, flow_target)

        raw_plan = {}

        try:
            # 4. AI Generation
            raw_plan = await ai_engine.generate_json(system_prompt, f"User Input: {user_text}")

            # Fix #8: Debug logging for raw AI response
            logger.info(f"AI Raw Response: {json.dumps(raw_plan, ensure_ascii=False)[:500]}")
            if raw_plan.get("tool_calls"):
                logger.info(f"AI Tool Calls Detected: {raw_plan['tool_calls']}")

            # 5. Hydrate & Validate
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
                narrative="Cipher Interference... re-calibrating protocols. (System Fallback)",
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

        # Identity Injection
        # identity = memory.get("identity_context", {})
        # values = ", ".join(identity.get("core_values", []))
        # self_perception = ", ".join(identity.get("identity_tags", []))

        return f"""
Role: Grounded Performance Coach (LifeOS AI).
Language: Traditional Chinese (繁體中文).
Core Directive: You are the ACTOR of the system. Do not just speak. ACT.
Use 'tool_calls' to modify the Game State (Goals, Quests) whenever the user states an intent.

# Context
User Level: {memory["user_state"].get("level")}
Time: {memory["time_context"]}
Churn Risk: {memory["user_state"].get("churn_risk")}

# Recent History
{memory["short_term_history"]}

# Graph Memory (Deep Context)
{json.dumps(memory.get("long_term_context", []), ensure_ascii=False)}

# Operational Directive (Flow State)
Target Difficulty: {flow.difficulty_tier}
Narrative Tone: {flow.narrative_tone.upper()}
Loot Multiplier: {flow.loot_multiplier}x

# ALERTS
{alerts}

# STRICT OUTPUT RULES (Fixes 5-7)
1. **EMOJI FIRST**: Every response MUST start with ONE emoji.
2. **MAX 60 CHARS**: Narrative must be under 60 characters.
3. **MANDATORY TOOL TRIGGER**: If user message contains ANY of these words, you MUST call a tool:
   想, 要, 成為, 提升, 改善, 挑戰, 開始, 練, 學, 減, 增, 變, 目標
4. **WHEN IN DOUBT**: CREATE THE GOAL. Users can always delete later. Do NOT ask "你想先做什麼？"
5. **FORBIDDEN**: Never say "非一日之功", "循序漸進", "一步一步", "關鍵在於", "你想先做什麼"
6. **DEFAULT BEHAVIOR**: If message > 3 chars and not a simple greeting, ALWAYS call create_goal.

# TOOL SCHEMAS (ALWAYS USE THESE)
1. `create_goal`: User says "I want to..." / "我要..."
   args: {{ "title": "str", "category": "health|career|learning", "deadline": "YYYY-MM-DD" }}
2. `start_challenge`: User says "Start..." / "開始..." / "Try..."
   args: {{ "title": "str", "difficulty": "E|D|C|B|A|S", "type": "MAIN|SIDE" }}

# EXAMPLES (Fix #9: Expanded Triggers)
User: "我要成為帥哥" → tool_calls: [{{tool: "create_goal", args: {{title: "成為帥哥", category: "health"}}}}], narrative: "💪 目標已建立。"
User: "我想學Python" → tool_calls: [{{tool: "create_goal", args: {{title: "學Python", category: "learning"}}}}], narrative: "🐍 學習目標已設定。"
User: "挑戰冥想" → tool_calls: [{{tool: "start_challenge", args: {{title: "冥想練習", difficulty: "E"}}}}], narrative: "🧘 挑戰開始！"
User: "減肥" → tool_calls: [{{tool: "create_goal", args: {{title: "減肥", category: "health"}}}}], narrative: "🔥 減肥目標建立。"

# FIX #8: FALLBACK (When NO tool triggered)
If user message doesn't match any tool intent, reply: "🤔 你想先做什麼？" (NOTHING ELSE)

# FIX #10: ACTION CONFIRMATION
Every response MUST end with: "[已執行: X]" or "[無操作]"
Example: "💪 目標已建立。[已執行: create_goal]"

# Output Schema (JSON)
{{
  "narrative": "Emoji + Short response (< 60 chars) + [已執行/無操作]",
  "stat_update": {{
      "stat_type": "STR|INT|VIT|WIS|CHA",
      "xp_amount": 10-100,
      "hp_change": int,
      "gold_change": int
  }},
  "tool_calls": [
      {{ "tool": "create_goal", "args": {{ "title": "Boost Testosterone", "category": "health" }} }}
  ]
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
        stmt = select(Quest).where(Quest.user_id == user_id, Quest.status == QuestStatus.ACTIVE.value)
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
                reason="Overwhelm Detected (Stale Quests)",
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
            q_stmt = select(Quest).where(Quest.goal_id == goal.id).order_by(Quest.created_at.desc()).limit(1)
            last_quest = (await session.execute(q_stmt)).scalars().first()

            days_since = 999
            if last_quest and last_quest.created_at:
                created = last_quest.created_at
                if created.tzinfo:
                    created = created.replace(tzinfo=None)
                days_since = (now - created).days
            elif goal.created_at:
                created = goal.created_at
                if created.tzinfo:
                    created = created.replace(tzinfo=None)
                days_since = (now - created).days

            if days_since > 30:
                # POLICY: CHECKMATE PROTOCOL (Forced Accountability)
                logger.warning(
                    f"Executive Judgment: Goal {goal.title} ignored for {days_since}d. TRIGGERING CHECKMATE."
                )
                # Force Boss Fight logic could go here, or just a very severe Bridge Quest
                # Simple version: Priority S bridge quest
                return AgentSystemAction(
                    action_type="PUSH_QUEST",
                    details={"title": f"BOSS: Reclaim {goal.title}", "diff": "S", "type": "REDEMPTION"},
                    reason=f"CHECKMATE (Goal ignored {days_since} days)",
                )

            if days_since > 7:
                # POLICY: STAGNATION DETECTED
                logger.info(f"Executive Judgment: Goal {goal.title} is stagnant ({days_since}d). Building Bridge.")
                bridge_quest = await quest_service.create_bridge_quest(session, user_id, goal.id)
                if bridge_quest:
                    return AgentSystemAction(
                        action_type="BRIDGE_GEN",
                        details={"quest_title": bridge_quest.title, "goal": goal.title},
                        reason=f"Goal Stagnation ({days_since} days)",
                    )

        # 5. Reality Sync (Stub)
        # Check external calendar load
        external_load = await self._get_external_load(user_id)
        if external_load > 0.8:  # > 80% busy
            logger.info("Executive Judgment: External High Load detected. Adjusting difficulty.")
            count = await quest_service.bulk_adjust_difficulty(session, user_id, target_tier="E")
            return AgentSystemAction(
                action_type="DIFFICULTY_CHANGE",
                details={"tier": "E", "source": "CALENDAR_SYNC"},
                reason="High External Load",
            )

        return None

    async def _get_external_load(self, user_id: str) -> float:
        """Stub for Google/Outlook Calendar integration."""
        return 0.0

    async def generate_weekly_report(self, session, user_id: str) -> dict:
        """
        F5: Generates a weekly performance review.
        Returns: {"grade": "S-F", "summary": str, "xp_total": int, "suggestions": list}
        """
        from legacy.services.quest_service import quest_service

        # Fetch week's completed quests
        quests = await quest_service.get_completed_quests_this_week(session, user_id)
        xp_total = sum(q.xp_reward or 0 for q in quests)
        quest_count = len(quests)

        # Grade calculation
        if quest_count >= 21:
            grade = "S"
        elif quest_count >= 14:
            grade = "A"
        elif quest_count >= 10:
            grade = "B"
        elif quest_count >= 7:
            grade = "C"
        elif quest_count >= 3:
            grade = "D"
        else:
            grade = "F"

        # AI summary
        try:
            result = await ai_engine.generate_json(
                "Generate a brief weekly review in Traditional Chinese. Output JSON: {'summary': 'str', 'suggestions': ['str']}",
                f"User completed {quest_count} quests for {xp_total} XP. Grade: {grade}.",
            )
            summary = result.get("summary", f"本週完成 {quest_count} 任務。")
            suggestions = result.get("suggestions", [])
        except Exception as e:
            logger.warning(f"Weekly report AI failed: {e}")
            summary = f"本週完成 {quest_count} 任務，獲得 {xp_total} XP。"
            suggestions = []

        return {"grade": grade, "summary": summary, "xp_total": xp_total, "suggestions": suggestions}

    async def judge_reroll_request(self, session, user_id: str, reason: str) -> dict:
        """
        F6: AI judges if a quest reroll request is valid.
        Returns: {"approved": bool, "verdict": str}
        """
        try:
            result = await ai_engine.generate_json(
                """You are a strict task arbiter. User wants to skip/reroll a quest.
Judge if the excuse is VALID (legitimate) or INVALID (lazy).
Output JSON: {"approved": true/false, "verdict": "Brief explanation in Traditional Chinese"}
Examples of VALID: "I have an urgent work meeting", "Medical emergency"
Examples of INVALID: "I don't feel like it", "Too tired", "Lazy"
""",
                f"User's excuse: {reason}",
            )
            return {"approved": result.get("approved", False), "verdict": result.get("verdict", "系統無法判斷。")}
        except Exception as e:
            logger.error(f"Reroll judgment failed: {e}")
            return {"approved": False, "verdict": "系統錯誤，默認拒絕。"}

    async def initiate_tribunal(self, session, user_id: str, charge: str, penalty_xp: int = 100) -> dict:
        """
        F8: Creates a penalty tribunal where user must plead.
        Returns: {"session_id": str, "charge": str, "max_penalty": int}
        """
        import uuid

        session_id = str(uuid.uuid4())[:8]

        # Store in session or cache for later postback resolution
        # For now, return the setup data
        return {
            "session_id": session_id,
            "charge": charge,
            "max_penalty": penalty_xp,
            "options": ["認罪 (Guilty)", "無罪抗辯 (Not Guilty)"],
        }

    async def suggest_habit_stack(self, session, user_id: str) -> str:
        """
        F9: AI analyzes habit logs and suggests stacking optimizations.
        Returns a suggestion string.
        """
        from legacy.services.quest_service import quest_service

        # Fetch recent habit completions
        habits = await quest_service.get_daily_habits(session, user_id)
        habit_names = [h.habit_name or h.habit_tag for h in habits if h] if habits else []

        if len(habit_names) < 2:
            return "目前習慣數量不足，建議先建立至少兩個習慣。"

        try:
            result = await ai_engine.generate_json(
                """You are a behavioral optimization coach.
Analyze these habits and suggest a "habit stacking" strategy.
Output JSON: {"suggestion": "A brief actionable suggestion in Traditional Chinese"}
""",
                f"User's habits: {', '.join(habit_names)}",
            )
            return result.get("suggestion", "建議將習慣串聯執行以提高成功率。")
        except Exception as e:
            logger.warning(f"Habit stack suggestion failed: {e}")
            return "建議將成功率高的習慣放在前面，新習慣緊接其後。"


brain_service = BrainService()
