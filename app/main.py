from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.migrations import run_migrations
from app.core.logging_middleware import LoggingMiddleware

# from app.api import webhook
# from app.services.scheduler import dda_scheduler
import asyncio
import logging
import os


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Resilience: Global Exception Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Database Migration
    if settings.AUTO_MIGRATE:
        try:
            logging.info("AUTO_MIGRATE enabled; running migrations.")

            # Critical: Ensure data directory exists for Ephemeral DB
            os.makedirs("./data", exist_ok=True)

            # Critical: For Ephemeral SQLite/Kuzu, force clean slate to avoid Lock/Schema errors

            # Critical: For Ephemeral SQLite/Kuzu, force clean slate to avoid Lock/Schema errors
            # 1. Clean SQLite
            if "sqlite" in str(settings.SQLALCHEMY_DATABASE_URI):
                # Extract path. typically "sqlite+aiosqlite:///./data/game.db"
                # Simple heuristic:
                if "game.db" in str(settings.SQLALCHEMY_DATABASE_URI):
                    db_path = "./data/game.db"  # Hardcoded based on our known config
                    if os.path.exists(db_path):
                        logging.warning(f"Removing stale DB at {db_path} for clean migration.")
                        try:
                            os.remove(db_path)
                        except OSError:
                            pass

            # 2. Clean KuzuDB (Graph)
            if settings.KUZU_DATABASE_PATH and os.path.exists(settings.KUZU_DATABASE_PATH):
                import shutil

                try:
                    shutil.rmtree(settings.KUZU_DATABASE_PATH, ignore_errors=True)
                    logging.warning(f"Removed stale KuzuDB at {settings.KUZU_DATABASE_PATH}")
                except Exception:
                    pass

            await asyncio.to_thread(run_migrations)

            # Seed Data (Shop Items)
            from app.core.seeding import seed_shop_items
            from app.core.database import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                await seed_shop_items(session)

        except Exception:
            logging.exception("Auto migration failed.")
            # Don't raise, try to start anyway to allow /health
            pass

    yield

    # Shutdown
    # if settings.ENABLE_SCHEDULER and os.environ.get("TESTING") != "1":
    #     dda_scheduler.shutdown()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)

# --- Logic Refactoring for Testability ---
from domain.models.game_result import GameResult
from app.core.dispatcher import dispatcher
from application.services.game_loop import game_loop
from app.core.database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


# 1. Define Independent Handlers
async def handle_attack(session, user_id: str, text: str) -> GameResult:
    """Handle attack command"""
    # In real logic, this would calculate damage, update DB, etc.
    return GameResult(text="⚔️ 你發動了攻擊！造成了 10 點傷害。", intent="attack")


async def handle_defend(session, user_id: str, text: str) -> GameResult:
    """Handle defend command"""
    return GameResult(text="🛡️ 你擺出了防禦姿態，傷害減少 50%。", intent="defend")


async def handle_ai_analysis(session, user_id: str, text: str) -> GameResult:
    """Handle natural language via BrainService (The Cortex) - Cognitive Upgrade."""
    from application.services.brain_service import brain_service
    from legacy.services.user_service import user_service
    from adapters.persistence.kuzu.adapter import get_kuzu_adapter
    from legacy.services.hp_service import hp_service
    from legacy.services.quest_service import quest_service

    # --- PHASE 4: THE PULSE (LAZY EVALUATION) ---
    # Trigger "Wake Up" protocols based on user returning
    user = await user_service.get_or_create_user(session, user_id)

    # 1. HP Drain
    drain_amount = await hp_service.calculate_daily_drain(session, user)

    # 2. Viper/Quest Push
    pushed_quests = await quest_service.trigger_push_quests(session, user_id)

    pulsed_events = {
        "drain_amount": drain_amount,
        "viper_taunt": f"System rebooted. {len(pushed_quests)} tasks pending." if pushed_quests else None,
    }

    # --- PHASE 5: BRAIN TRANSPLANT ---
    # Use Cortex instead of Lizard Brain
    plan = await brain_service.think_with_session(session, user_id, text, pulsed_events=pulsed_events)

    # Execute Plan
    if plan.stat_update:
        # Applying Brain's Stat Directives
        update_data = plan.stat_update
        if update_data.stat_type:
            stat_key = update_data.stat_type.lower()
            if hasattr(user, stat_key):
                curr = getattr(user, stat_key) or 0
                setattr(user, stat_key, curr + 1)  # Simplified for now, mostly driven by Brain's specific logic later

        # Apply HP/Gold changes directly
        if update_data.hp_change != 0:
            await hp_service.apply_hp_change(session, user, update_data.hp_change, source="brain_reward")

        if update_data.gold_change != 0:
            user.gold = (user.gold or 0) + update_data.gold_change

        # XP
        if update_data.xp_amount > 0:
            user.xp = (user.xp or 0) + update_data.xp_amount

        await session.commit()

    # Record Event to Graph
    kuzu_adapter = get_kuzu_adapter()
    kuzu_adapter.record_user_event(
        user_id,
        "ACTION",
        {
            "content": plan.narrative,
            "stat_type": plan.stat_update.stat_type if plan.stat_update else "none",
            "raw_text": text,
            "flow_tone": plan.flow_state.get("tone", "neutral"),
        },
    )

    # ---------------------------------------------------------
    # Intent Dispatcher (Deep Integration)
    # ---------------------------------------------------------
    # Execute Tool Calls
    from legacy.services.flex_renderer import flex_renderer

    # Fix #4: Debug logging for tool calls
    logger.info(f"AI Tool Calls Count: {len(plan.tool_calls)}")
    if plan.tool_calls:
        logger.info(f"Tool Calls: {plan.tool_calls}")

    tool_flex_messages = []
    for tool_call in plan.tool_calls:
        try:
            tool_name = tool_call.get("tool")
            args = tool_call.get("args", {})
            logger.info(f"Executing AI Tool: {tool_name} with {args}")

            if tool_name == "create_goal":
                # AI Arg Mapping
                title = args.get("title", "New Goal")
                category = args.get("category", "general")
                # Create Goal (Logic: QuestService)
                from legacy.models.quest import GoalStatus

                _goal, _ai_plan = await quest_service.create_new_goal(session, user_id, goal_text=title)
                # Generate Flex Card
                flex_msg = flex_renderer.render_goal_card(title=title, category=category)
                tool_flex_messages.append(flex_msg)

            elif tool_name == "start_challenge":
                # AI Arg Mapping
                title = args.get("title", "Challenge")
                difficulty = args.get("difficulty", "E")
                # Create Quest
                quest = await quest_service.create_quest(
                    session, user_id, title=title, description="AI Challenge", difficulty=difficulty
                )
                # Generate Flex Card
                xp = getattr(quest, "xp_reward", 50)
                flex_msg = flex_renderer.render_quest_brief(title=title, difficulty=difficulty, xp_reward=xp)
                tool_flex_messages.append(flex_msg)

        except Exception as e:
            logger.error(f"Tool Execution Failed ({tool_name}): {e}", exc_info=True)
            plan.narrative += f"\n[SYSTEM ERROR: {tool_name}]"

    result_meta = {"plan": plan.model_dump()}
    if tool_flex_messages:
        result_meta["flex_messages"] = tool_flex_messages
        logger.info(f"Generated {len(tool_flex_messages)} Flex messages")

    # Fix #5: Add Quick Reply buttons for common actions
    from linebot.v3.messaging import QuickReply, QuickReplyItem, MessageAction

    quick_reply = QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label="📊 狀態", text="狀態")),
            QuickReplyItem(action=MessageAction(label="📋 任務", text="任務")),
            QuickReplyItem(action=MessageAction(label="🎯 新目標", text="我想設定新目標")),
        ]
    )
    result_meta["quick_reply"] = quick_reply

    return GameResult(text=plan.narrative, intent="ai_response", metadata=result_meta)


# =============================================================================
# Phase 3: Chinese Command Handlers (Fixes 1-4)
# =============================================================================


async def handle_status(session: AsyncSession, user_id: str, text: str) -> GameResult:
    """Handler for '狀態' command - returns user status Flex card."""
    from legacy.services.user_service import user_service
    from legacy.services.flex_renderer import flex_renderer

    user = await user_service.get_or_create_user(session, user_id)
    flex = flex_renderer.render_status(user)
    return GameResult(text="📊 玩家狀態", intent="status", metadata={"flex_message": flex})


async def handle_quests(session: AsyncSession, user_id: str, text: str) -> GameResult:
    """Handler for '任務' command - returns quest list Flex card."""
    from legacy.services.quest_service import quest_service
    from legacy.services.flex_renderer import flex_renderer

    quests = await quest_service.get_daily_quests(session, user_id)
    if quests:
        flex = flex_renderer.render_quest_list(quests)
        return GameResult(text="📋 今日任務", intent="quests", metadata={"flex_message": flex})
    else:
        return GameResult(text="📭 目前沒有任務。試試說「我想...」來設定新目標！", intent="quests")


async def handle_new_goal(session: AsyncSession, user_id: str, text: str) -> GameResult:
    """Handler for '新目標' or goal-setting intent - prompts or creates goal."""
    from legacy.services.quest_service import quest_service
    from legacy.services.flex_renderer import flex_renderer

    # Extract goal from text if present
    goal_text = text.replace("新目標", "").replace("我想設定", "").replace("我想", "").strip()

    if len(goal_text) > 3:
        # User provided a goal - create it directly
        goal, ai_plan = await quest_service.create_new_goal(session, user_id, goal_text=goal_text)
        flex = flex_renderer.render_goal_card(title=goal_text, category="general")
        return GameResult(
            text=f"🎯 目標「{goal_text}」已建立！[已執行: create_goal]",
            intent="goal_created",
            metadata={"flex_message": flex},
        )
    else:
        # No goal text - prompt user
        return GameResult(text="🎯 你想達成什麼目標？（例如：學Python、減肥、早起）", intent="goal_prompt")


# 2. Register Strategies - Chinese Commands FIRST
dispatcher.register(lambda t: t.strip() in ["狀態", "status", "狀態 "], handle_status)
dispatcher.register(lambda t: t.strip() in ["任務", "quests", "任務 "], handle_quests)
dispatcher.register(
    lambda t: "新目標" in t or "設定目標" in t or "設定新目標" in t or t.strip() == "我想設定新目標",
    handle_new_goal,
)

# Legacy (keep for compatibility)
dispatcher.register(lambda t: t.lower().strip() == "attack", handle_attack)
dispatcher.register(lambda t: t.lower().strip() == "defend", handle_defend)

# Register Default AI Handler (LAST - catches everything else)
dispatcher.register_default(handle_ai_analysis)


# 3. Expose Core Logic Wrapper
# 3. Expose Core Logic Wrapper
async def process_game_logic(user_id: str, text: str, session: AsyncSession = None) -> GameResult:
    """
    Core Game Logic Entry Point (Decoupled from HTTP)
    Refactored to allow direct unit testing without Webhook signature.
    Dependency Injection: pass 'session' for testing, or it defaults to AsyncSessionLocal.
    """
    if session:
        return await game_loop.process_message(session, user_id, text)

    async with AsyncSessionLocal() as session:
        return await game_loop.process_message(session, user_id, text)


# -----------------------------------------

# Include Router
# New LINE webhook (clean architecture)
from app.api import line_webhook
from app.api import nerves
from app.api import chat  # [NEW] Phase 5: NPC Chat

app.include_router(line_webhook.router, prefix="", tags=["line"])
app.include_router(nerves.router, prefix="/api", tags=["nerves"])
app.include_router(chat.router, prefix="/api", tags=["chat"])  # [NEW] Phase 5: NPC Chat

# Legacy routers moved to legacy/api
# from app.api import users
# app.include_router(users.router, prefix="/users", tags=["users"])

# from app.api import dashboard
# app.include_router(dashboard.router, tags=["dashboard"])

# Removed simple health check


# --- Resilience: Health Check ---
@app.get("/health")
async def health_check():
    """
    Liveness Probe.
    Checks DB connection and returns version.
    """
    health_status = {
        "status": "ok",
        "version": settings.VERSION,
        "database": "unknown",
        "timestamp": os.getenv("WEBSITE_HOSTNAME", "local"),
    }

    try:
        # Simple DB Check
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
        # Log the full error but don't crash the probe (return 200 with degraded status)
        logging.error(f"Health Check Failed: {e}", exc_info=True)


# --- Logic Refactoring for Testability ---
# (Keep existing game logic intact below if needed, or import it)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
