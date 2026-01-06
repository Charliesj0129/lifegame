from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.services.user_service import user_service

router = APIRouter()


@router.get("/{user_id}/status")
async def get_user_status(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    attr_labels = {
        "STR": "力量",
        "INT": "智力",
        "VIT": "體力",
        "WIS": "智慧",
        "CHA": "魅力",
    }

    return {
        "id": user.id,
        "name": user.name,
        "level": user.level,
        "attributes": {
            attr_labels["STR"]: user.str,
            attr_labels["INT"]: user.int,
            attr_labels["VIT"]: user.vit,
            attr_labels["WIS"]: user.wis,
            attr_labels["CHA"]: user.cha,
        },
        "currencies": {"gold": user.gold, "xp": user.xp if hasattr(user, "xp") else 0},
        "vitals": {
            "hp": user.hp,
            "max_hp": user.max_hp,
            "is_hollowed": user.is_hollowed,
        },
    }


from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.gamification import UserItem


@router.get("/{user_id}/inventory")
async def get_user_inventory(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(UserItem)
        .where(UserItem.user_id == user_id)
        .options(selectinload(UserItem.item))
    )
    user_items = result.scalars().all()

    inventory = []
    for ui in user_items:
        inventory.append(
            {
                "item_id": ui.item_id,
                "name": ui.item.name,
                "quantity": ui.quantity,
                "rarity": ui.item.rarity,
                "type": ui.item.type,
                "description": ui.item.description,
            }
        )

    return inventory
