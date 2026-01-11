from dataclasses import dataclass
from typing import Optional, Tuple
from datetime import date, timedelta

@dataclass
class RivalEncounterResult:
    missed_days: int
    rival_xp_gain: int
    rival_level_up: bool
    theft_xp: int
    theft_gold: int
    should_debuff: bool
    debuff_attribute: Optional[str] = None

class RivalRules:
    @staticmethod
    def calculate_inactivity_penalty(
        last_active_date: Optional[date], 
        current_date: date,
        user_xp: int, 
        user_gold: int,
        user_level: int,
        rival_level: int,
        rival_xp: int
    ) -> RivalEncounterResult:
        """
        Calculates consequences of user inactivity.
        Pure logic: No DB, No AI.
        """
        if not last_active_date:
            return RivalEncounterResult(0, 0, False, 0, 0, False)

        delta = current_date - last_active_date
        missed_days = delta.days - 1

        if missed_days <= 0:
            return RivalEncounterResult(0, 0, False, 0, 0, False)

        # 1. Rival Growth
        xp_gain = missed_days * 100
        new_rival_xp = rival_xp + xp_gain
        # Simple Leveling: Lv = 1 + XP // 1000
        # Check if new total XP pushes to next level bracket
        projected_level = 1 + (new_rival_xp // 1000)
        level_up = projected_level > rival_level

        # 2. Theft (5% per day)
        theft_xp = int(user_xp * 0.05 * missed_days)
        theft_gold = int(user_gold * 0.05 * missed_days)

        # 3. Debuff logic (Only if Rival > User)
        should_debuff = rival_level > user_level

        return RivalEncounterResult(
            missed_days=missed_days,
            rival_xp_gain=xp_gain,
            rival_level_up=level_up,
            theft_xp=theft_xp,
            theft_gold=theft_gold,
            should_debuff=should_debuff
        )
