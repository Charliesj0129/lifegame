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

# Include Router
# New LINE webhook (clean architecture)
from app.api import line_webhook
app.include_router(line_webhook.router, prefix="", tags=["line"])

# Legacy webhook removed
# from legacy.webhook import router as legacy_webhook_router
# app.include_router(legacy_webhook_router, prefix="/legacy", tags=["line-legacy"])

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
