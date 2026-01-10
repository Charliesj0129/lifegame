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
                    db_path = "./data/game.db" # Hardcoded based on our known config
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
    """Handle natural language via AI Engine and Persist Changes."""
    from legacy.services.ai_engine import ai_engine
    from legacy.services.user_service import user_service
    from adapters.persistence.kuzu.adapter import get_kuzu_adapter
    import time
    
    # 1. Analyze action
    analysis = await ai_engine.analyze_action(text)
    
    # 2. Update User Stats (SQLite)
    user = await user_service.get_or_create_user(session, user_id)
    stat = analysis.get("stat_type", "").lower() # str, int, vit...
    if hasattr(user, stat):
        current_val = getattr(user, stat)
        setattr(user, stat, current_val + 1)
        await session.commit()
    
    # 3. Log to Graph (Kuzu)
    kuzu_adapter = get_kuzu_adapter()
    # Ensure User exists in Graph
    kuzu_adapter.add_user_if_not_exists(user_id, user.name or "User")
    # Add Event
    event_id = f"evt_{int(time.time())}"
    kuzu_adapter.add_event(
        user_id, 
        event_id, 
        "ACTION", 
        analysis.get("narrative", text), 
        int(time.time())
    )
    
    # Convert AI JSON to GameResult
    narrative = analysis.get("narrative", "...")
    return GameResult(
        text=narrative, 
        intent="ai_response", 
        metadata={"analysis": analysis}
    )

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
from app.api import chat # [NEW] Phase 5: NPC Chat

app.include_router(line_webhook.router, prefix="", tags=["line"])
app.include_router(nerves.router, prefix="/api", tags=["nerves"])
app.include_router(chat.router, prefix="/api", tags=["chat"]) # [NEW] Phase 5: NPC Chat

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
        "timestamp": os.getenv("WEBSITE_HOSTNAME", "local")
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
        
    return health_status


# --- Logic Refactoring for Testability ---
# (Keep existing game logic intact below if needed, or import it)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
