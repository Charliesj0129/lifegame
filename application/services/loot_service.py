import logging
import random
from dataclasses import dataclass, field
from typing import List, Optional
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
    """

    # Baseline expected rewards by difficulty (User's internal model)
    BASE_XP = {"E": 10, "D": 20, "C": 50, "B": 100, "A": 200, "S": 500}

    def calculate_reward(self, difficulty: str, current_tier: str, churn_risk: str = "LOW") -> LootResult:
        """
        Calculates reward with RPE logic.

        Algorithm:
        1. Expected = Baseline for Difficulty.
        2. Flow Multiplier = From FlowController (e.g. 1.2x if Churn Risk).
        3. RNG Variance = +/- 20% standard, occasional 200% Jackpot.
        4. Actual = Base * Flow * RNG.
        5. RPE = Actual - Expected.
        """
        base_xp = self.BASE_XP.get(difficulty, 20)

        # 1. Get Flow Context (Are we boosting loot?)
        # Use FlowController to determine multiplier (e.g. EOMM triggers)
        state = flow_controller.calculate_next_state(
            current_tier=current_tier,
            recent_performance=[],  # No perf history passed yet
            churn_risk=churn_risk,
        )
        loot_multiplier = state.loot_multiplier

        if loot_multiplier > 1.0:
            logger.info(f"Loot Boost Active: {loot_multiplier}x (Risk: {churn_risk})")

        # Anti-Exploit Cap
        MAX_MULTIPLIER = 5.0
        loot_multiplier = min(loot_multiplier, MAX_MULTIPLIER)

        # Check for Jackpot (5% chance)
        is_jackpot = random.random() < 0.05
        rng_factor = 2.0 if is_jackpot else random.uniform(0.8, 1.2)

        actual_xp = int(base_xp * loot_multiplier * rng_factor)

        # RPE Calculation
        # RPE = Actual Reward - Expected Reward
        # Expected Reward is roughly Base XP.
        rpe_score = actual_xp - base_xp

        # Determine Narrative Flavor based on RPE
        flavor = "Standard"
        if is_jackpot:
            flavor = "Jackpot"  # High Positive RPE
        elif rpe_score > (base_xp * 0.5):
            flavor = "Lucky"  # Moderate Positive RPE
        elif rpe_score < -(base_xp * 0.1):
            flavor = "Disappointing"  # Negative RPE

        logger.info(f"Loot Gen: Diff={difficulty} Base={base_xp} Actual={actual_xp} RPE={rpe_score} ({flavor})")

        return LootResult(
            xp=actual_xp,
            gold=actual_xp // 10,  # Simple Gold conversion
            rpe_score=rpe_score,
            narrative_flavor=flavor,
        )


loot_service = LootService()
