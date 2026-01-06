from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.migrations import run_migrations
from app.core.logging_middleware import LoggingMiddleware
from app.api import webhook
from app.services.scheduler import dda_scheduler
import asyncio
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    if settings.AUTO_MIGRATE:
        try:
            logging.info("AUTO_MIGRATE enabled; running migrations.")
            await asyncio.to_thread(run_migrations)
        except Exception:
            logging.exception("Auto migration failed.")
            raise
    
    # Start scheduler (only if enabled and not in testing mode)
    if settings.ENABLE_SCHEDULER and os.environ.get("TESTING") != "1":
        dda_scheduler.start()
    
    yield
    
    # Shutdown
    if settings.ENABLE_SCHEDULER and os.environ.get("TESTING") != "1":
        dda_scheduler.shutdown()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.add_middleware(LoggingMiddleware)

# Include Router
app.include_router(webhook.router, prefix="", tags=["line"])
from app.api import users
app.include_router(users.router, prefix="/users", tags=["users"])

from app.api import health
app.include_router(health.router, tags=["ops"])

from app.api import dashboard
app.include_router(dashboard.router, tags=["dashboard"])

# Removed simple health check

@app.get("/")
async def root():
    return {"message": "Welcome to Life Gamification Agent System"}

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="app/static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
