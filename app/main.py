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
# Auto-Run Migration on Startup (For M6 Schema Updates)
@app.get("/deploy_schema")
async def manual_migration():
    import traceback
    try:
        from scripts.migrate_m7 import migrate
        await migrate()
        return {"status": "Migration M7 Executed Successfully"}
    except BaseException:
        tb = traceback.format_exc()
        logging.error(f"Migration Failed: {tb}")
        return {"status": "Failed", "error": tb}

@app.get("/setup_rich_menus")
async def setup_rich_menus():
    from app.services.rich_menu_service import rich_menu_service
    try:
        mappings = rich_menu_service.setup_menus()
        return {"status": "Rich Menus Configured", "mappings": mappings}
    except Exception as e:
        return {"status": "Failed", "error": str(e)}

# Include Router
app.include_router(webhook.router, prefix="", tags=["line"])
from app.api import users
app.include_router(users.router, prefix="/users", tags=["users"])

from app.api import health
app.include_router(health.router, tags=["ops"])

# Removed simple health check

@app.get("/")
async def root():
    return {"message": "Welcome to Life Gamification Agent System"}

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="app/static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
