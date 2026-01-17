import logging
import random
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql.expression import func

# TODO: Move these models to application/domain later
from app.models.gamification import Item, ItemRarity, UserItem
from application.services.brain.flow_controller import flow_controller

logger = logging.getLogger(__name__)


@dataclass
class LootResult:
    xp: int
    gold: int = 0
    items: List[str] = field(default_factory=list)
    rpe_score: float = 0.0
    narrative_flavor: str = "Standard"


class LootService:
    """
    Manages Reward Distribution and Addiction Mechanics (RPE).
    Also handles Item Drops (Legacy Logic Merged).
    """

    # Baseline expected rewards by difficulty (User's internal model)
    BASE_XP = {"E": 10, "D": 20, "C": 50, "B": 100, "A": 200, "S": 500}

    def __init__(self):
        # Legacy Item Drop Config
        self.base_drop_rate = 0.20
        self.rarity_weights = {
            ItemRarity.COMMON: 50.0,
            ItemRarity.UNCOMMON: 35.0,
            ItemRarity.RARE: 10.0,
            ItemRarity.EPIC: 4.0,
            ItemRarity.LEGENDARY: 1.0,
        }
        self.diff_multipliers = {
            "F": 0.5,
            "E": 1.0,
            "D": 1.2,
            "C": 1.5,
            "B": 2.0,
            "A": 3.0,
        }

    def calculate_reward(self, difficulty: str, current_tier: str, churn_risk: str = "LOW") -> LootResult:
        """
        Calculates reward with RPE logic.
        """
        base_xp = self.BASE_XP.get(difficulty, 20)

        # 1. Get Flow Context
        state = flow_controller.calculate_next_state(
            current_tier=current_tier,
            recent_performance=[],
            churn_risk=churn_risk,
        )
        loot_multiplier = state.loot_multiplier

        if loot_multiplier > 1.0:
            logger.info(f"Loot Boost Active: {loot_multiplier}x (Risk: {churn_risk})")

        # Anti-Exploit Cap
        loot_multiplier = min(loot_multiplier, 5.0)

        # Check for Jackpot (5% chance)
        is_jackpot = random.random() < 0.05
        rng_factor = 2.0 if is_jackpot else random.uniform(0.8, 1.2)

        actual_xp = int(base_xp * loot_multiplier * rng_factor)

        # RPE Calculation
        rpe_score = actual_xp - base_xp

        flavor = "Standard"
        if is_jackpot:
            flavor = "Jackpot"
        elif rpe_score > (base_xp * 0.5):
            flavor = "Lucky"
        elif rpe_score < -(base_xp * 0.1):
            flavor = "Disappointing"

        logger.info(f"Loot Gen: Diff={difficulty} Base={base_xp} Actual={actual_xp} RPE={rpe_score} ({flavor})")

        return LootResult(
            xp=actual_xp,
            gold=actual_xp // 10,
            rpe_score=rpe_score,
            narrative_flavor=flavor,
        )

    # --- Legacy Item Drop Logic (Ported) ---

    def _roll_for_drop(self, difficulty: str) -> bool:
        multiplier = self.diff_multipliers.get(difficulty, 1.0)
        chance = self.base_drop_rate * multiplier
        if chance > 1.0:
            chance = 1.0
        return random.random() < chance

    def _select_rarity(self) -> ItemRarity:
        rarities = list(self.rarity_weights.keys())
        weights = list(self.rarity_weights.values())
        return random.choices(rarities, weights=weights, k=1)[0]

    async def calculate_drop(self, session: AsyncSession, difficulty: str, force_drop: bool = False) -> Item | None:
        if not force_drop and not self._roll_for_drop(difficulty):
            return None

        target_rarity = self._select_rarity()

        result = await session.execute(
            select(Item).where(Item.rarity == target_rarity).order_by(func.random()).limit(1)
        )
        item = result.scalars().first()

        # Fallback to Common if empty
        if not item:
            result = await session.execute(
                select(Item).where(Item.rarity == ItemRarity.COMMON).order_by(func.random()).limit(1)
            )
            item = result.scalars().first()

        return item

    async def grant_item(self, session: AsyncSession, user_id: str, item: Item) -> UserItem:
        result = await session.execute(select(UserItem).where(UserItem.user_id == user_id, UserItem.item_id == item.id))
        user_item = result.scalars().first()

        if user_item:
            user_item.quantity += 1
        else:
            user_item = UserItem(user_id=user_id, item_id=item.id, quantity=1)
            session.add(user_item)

        await session.commit()
        await session.refresh(user_item)
        return user_item

    async def grant_guaranteed_drop(
        self, session: AsyncSession, user_id: str, min_rarity: ItemRarity = ItemRarity.RARE
    ) -> Item | None:
        order = [ItemRarity.COMMON, ItemRarity.UNCOMMON, ItemRarity.RARE, ItemRarity.EPIC, ItemRarity.LEGENDARY]
        try:
            min_index = order.index(min_rarity)
        except ValueError:
            min_index = order.index(ItemRarity.RARE)

        eligible = order[min_index:]
        result = await session.execute(select(Item).where(Item.rarity.in_(eligible)).order_by(func.random()).limit(1))
        item = result.scalars().first()
        if not item:
            return None
        await self.grant_item(session, user_id, item)
        return item


loot_service = LootService()
