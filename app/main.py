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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Database Migration
    if settings.AUTO_MIGRATE:
        try:
            logging.info("AUTO_MIGRATE enabled; running migrations.")
            await asyncio.to_thread(run_migrations)
        except Exception:
            logging.exception("Auto migration failed.")
            raise

    # Start scheduler (only if enabled and not in testing mode)
    # Scheduler moved to legacy
    # if settings.ENABLE_SCHEDULER and os.environ.get("TESTING") != "1":
    #     dda_scheduler.start()

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
    from adapters.persistence.kuzu_adapter import get_kuzu_adapter
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
async def process_game_logic(user_id: str, text: str) -> GameResult:
    """
    Core Game Logic Entry Point (Decoupled from HTTP)
    Refactored to allow direct unit testing without Webhook signature.
    """
    async with AsyncSessionLocal() as session:
        return await game_loop.process_message(session, user_id, text)

# -----------------------------------------

# Include Router
# New LINE webhook (clean architecture)
from app.api import line_webhook
app.include_router(line_webhook.router, prefix="", tags=["line"])

from app.api import nerves
app.include_router(nerves.router, prefix="/api", tags=["nerves"])

# Legacy routers moved to legacy/api
# from app.api import users
# app.include_router(users.router, prefix="/users", tags=["users"])

# from app.api import dashboard
# app.include_router(dashboard.router, tags=["dashboard"])

# Removed simple health check


@app.get("/")
async def root():
    return {"message": "Welcome to Life Gamification Agent System"}


from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="app/static"), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
