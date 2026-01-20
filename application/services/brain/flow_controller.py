import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)


@dataclass
class FlowState:
    difficulty_tier: str  # S, A, B, C, D, E
    loot_multiplier: float
    narrative_tone: str  # "Challenge", "Encourage", "Relax"


class FlowController:
    """
    Implements Behavioral Engineering & DDA:
    1. PID Control for Flow/Difficulty.
    2. Fogg Model (B=MAP) for Triggers.
    3. AI Director for Stress Pacing.
    4. EOMM for Churn Prevention.
    """

    TIERS = ["E", "D", "C", "B", "A", "S"]
    TIER_VALUES = {"E": 1, "D": 2, "C": 3, "B": 4, "A": 5, "S": 6}

    # PID Constants (Tunable)
    Kp = 0.5
    Ki = 0.1
    Kd = 0.2

    def calculate_next_state(
        self,
        current_tier: str,
        recent_performance: List[bool],  # True=Success, False=Fail
        churn_risk: str = "LOW",
        stress_score: float = 0.0,
        last_pity_at: Optional[float] = None,
        pid_state: Optional[Any] = None,  # UserPIDState model
    ) -> FlowState:
        # 1. EOMM Safety Net (Immediate Override)
        if churn_risk == "HIGH":
            # Rate Limit Check
            import time

            now = time.time()
            if last_pity_at and (now - last_pity_at) < 86400:  # 24 Hours
                logger.info("EOMM Blocked (Rate Limit)")
                return FlowState(difficulty_tier="E", loot_multiplier=1.0, narrative_tone="Encourage")

            logger.info("EOMM Triggered: Forcing Easy Win due to Churn Risk")
            return FlowState(difficulty_tier="E", loot_multiplier=2.0, narrative_tone="Encourage")

        # 2. AI Director (Stress Pacing)
        # If stress is too high (accumulated intensity), force Relax phase
        if stress_score > 0.8:
            logger.info("AI Director Triggered: Forced Relaxation Phase")
            return FlowState(difficulty_tier="D", loot_multiplier=1.0, narrative_tone="Relax")

        # 3. PID Controller for DDA
        # Target: ~70% Win Rate (Flow Channel)
        target_win_rate = 0.7

        if not recent_performance:
            return FlowState(difficulty_tier=current_tier, loot_multiplier=1.0, narrative_tone="Challenge")

        current_win_rate = sum(recent_performance) / len(recent_performance)

        # PID Calculation
        error = current_win_rate - target_win_rate
        
        # Default state values
        integral = 0.0
        last_error = 0.0
        
        if pid_state:
            integral = pid_state.integral or 0.0
            last_error = pid_state.last_error or 0.0
            
        # Integral Term (Accumulated Error)
        integral += error
        # Anti-windup clamping
        integral = max(-2.0, min(2.0, integral))
        
        # Derivative Term (Trend)
        derivative = error - last_error
        
        # Update State
        if pid_state:
            pid_state.integral = integral
            pid_state.last_error = error
            # Note: Caller is responsible for committing changes to DB
            
        # PID Output
        pid_output = (self.Kp * error) + (self.Ki * integral) + (self.Kd * derivative)
        
        logger.info(f"DDA PID: err={error:.2f}, int={integral:.2f}, der={derivative:.2f}, out={pid_output:.2f}")

        # Map PID output to tier adjustment
        adjustment = 0
        if pid_output < -0.3:  # Failing -> Reduce
            adjustment = -1
        elif pid_output > 0.2:  # Bored -> Increase
            adjustment = 1

        # Apply Adjustment
        current_val = self.TIER_VALUES.get(current_tier, 1)
        new_val = max(1, min(6, current_val + adjustment))
        new_tier = self.TIERS[new_val - 1]

        # Loot & Tone based on result
        loot_mult = 1.0
        tone = "Challenge"

        if adjustment < 0:
            tone = "Encourage"  # Don't give up
            loot_mult = 1.2  # Pity boost
        elif adjustment > 0:
            tone = "Respect"  # You are strong

        return FlowState(difficulty_tier=new_tier, loot_multiplier=loot_mult, narrative_tone=tone)

    def evaluate_fogg_trigger(
        self,
        motivation_score: float,  # 0.0 - 1.0 (e.g. Streak, Time of Day)
        friction_estimate: float,  # 0.0 - 1.0 (1.0 = Max Friction/Hard)
        prompt_salience: float = 1.0,
    ) -> bool:
        """
        B = M * A * P
        Ability (A) ~= 1 / Friction.
        If M * A > Threshold, then Trigger !
        """
        # Avoid div by zero
        friction = max(0.1, friction_estimate)
        ability = 1.0 / friction

        # Action Line Equation (Model): M + A > Const ?
        # Or B = M * A. Let's use Multiplicative.
        behavior_potential = motivation_score * ability * prompt_salience

        # Activation Threshold
        THRESHOLD = 1.5

        return behavior_potential > THRESHOLD


flow_controller = FlowController()
