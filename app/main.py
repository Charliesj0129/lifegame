from fastapi import FastAPI
from app.core.config import settings
from app.core.migrations import run_migrations
from app.api import webhook
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.on_event("startup")
async def auto_migrate() -> None:
    if not settings.AUTO_MIGRATE:
        return
    try:
        logging.info("AUTO_MIGRATE enabled; running migrations.")
        await asyncio.to_thread(run_migrations)
    except Exception:
        logging.exception("Auto migration failed.")
        raise

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
