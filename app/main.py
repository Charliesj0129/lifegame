from fastapi import FastAPI
from app.core.config import settings
from app.api import webhook
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Auto-Run Migration on Startup (For M6 Schema Updates)
@app.on_event("startup")
async def startup_event():
    from scripts.migrate_m6 import migrate
    try:
        await migrate()
        logging.info("Startup Migration M6 executed.")
    except Exception as e:
        logging.error(f"Startup Migration Failed: {e}")

# Include Router
app.include_router(webhook.router, prefix="", tags=["line"])
from app.api import users
app.include_router(users.router, prefix="/users", tags=["users"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.VERSION}

@app.get("/")
async def root():
    return {"message": "Welcome to Life Gamification Agent System"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
