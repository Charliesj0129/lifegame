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
    for tool_call in plan.tool_calls:
        try:
            tool_name = tool_call.get("tool")
            args = tool_call.get("args", {})
            logger.info(f"Executing AI Tool: {tool_name} with {args}")

            if tool_name == "create_goal":
                # AI Arg Mapping
                title = args.get("title", "New Goal")
                # category = args.get("category", "health") # Unused
                # Create Goal (Logic: QuestService)
                # Map to create_new_goal(session, user_id, goal_text)
                from legacy.models.quest import GoalStatus

                _goal, _ai_plan = await quest_service.create_new_goal(session, user_id, goal_text=title)
                plan.narrative += f"\n[SYSTEM: Goal '{title}' Created & Decomposed]"

            elif tool_name == "start_challenge":
                # AI Arg Mapping
                title = args.get("title", "Challenge")
                difficulty = args.get("difficulty", "E")
                # Create Quest
                _quest = await quest_service.create_quest(
                    session, user_id, title=title, description="AI Challenge", difficulty=difficulty
                )
                plan.narrative += f"\n[SYSTEM: Quest '{title}' ({difficulty}) Started]"

        except Exception as e:
            logger.error(f"Tool Execution Failed ({tool_name}): {e}", exc_info=True)
            plan.narrative += f"\n[SYSTEM ERROR: Could not execute {tool_name}]"

    return GameResult(text=plan.narrative, intent="ai_response", metadata={"plan": plan.dict()})


# 2. Register Strategies
dispatcher.register(lambda t: t.lower().strip() == "attack", handle_attack)
dispatcher.register(lambda t: t.lower().strip() == "defend", handle_defend)

# Register Default AI Handler
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
