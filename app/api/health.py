import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Checks if the API is running and the database is accessible.
    """
    logger.info("Health Check Accessed")
    try:
        # Lightweight query to check connection
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected", "version": "0.1.0"}
    except Exception as e:
        logger.error(f"Health Check Failed: {e}")
        # Return 503 Service Unavailable if DB is down
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "db": "disconnected", "error": str(e)},
        )
