from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from legacy.services.user_service import user_service
from legacy.services.rival_service import rival_service
from legacy.models.quest import QuestStatus, GoalStatus
import logging

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


@router.get("/dashboard/{user_id}", response_class=HTMLResponse)
async def get_dashboard(request: Request, user_id: str, db: AsyncSession = Depends(get_db)):
    """
    Renders the LifeGame Dashboard for a specific user.
    """
    try:
        # 1. Fetch User Data
        user = await user_service.get_user(db, user_id)
        if not user:
            # For new users visiting dashboard first (unlikely but possible via LIFF)
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": "User Not Found"},
                status_code=404,
            )

        # 2. Fetch Rival Data
        rival = await rival_service.get_rival(db, user_id)
        rival_level = rival.level if rival else 1
        rival_status = "Dominating" if rival_level > (user.level + 2) else "Active"

        # 3. Fetch Active Quests
        from sqlalchemy import select
        from legacy.models.quest import Quest, Goal

        # Active Quests
        stmt = select(Quest).where(Quest.user_id == user_id, Quest.status != QuestStatus.DONE.value)
        result = await db.execute(stmt)
        active_quests = result.scalars().all()

        # Active Goal
        stmt_goal = select(Goal).where(Goal.user_id == user_id, Goal.status == GoalStatus.ACTIVE.value)
        res_goal = await db.execute(stmt_goal)
        active_goal = res_goal.scalars().first()

        # 4. Inventory
        from legacy.models.gamification import UserItem, Item

        stmt_inv = select(UserItem, Item).join(Item).where(UserItem.user_id == user_id)
        res_inv = await db.execute(stmt_inv)
        # List of (UserItem, Item) tuples
        inventory_items = []
        for ui, i in res_inv:
            inventory_items.append(
                {
                    "name": i.name,
                    "quantity": ui.quantity,
                    "icon": "📦",  # Placeholder
                    "desc": i.description,
                    "price": i.price if hasattr(i, "price") else 0,
                }
            )

        # 5. Render
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": user,
                "rival": rival,
                "rival_status": rival_status,
                "quests": active_quests,
                "goal": active_goal,
                "inventory": inventory_items,
                "stats": {"STR": 10, "INT": 12, "VIT": 8, "DEX": 9, "LUK": 5},
            },
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        logger.error(f"Dashboard Error: {e}", exc_info=True)
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": f"Internal Error: {e}"},
            status_code=500,
        )
