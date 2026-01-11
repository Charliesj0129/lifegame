import enum

class HPStatus(str, enum.Enum):
    HEALTHY = "HEALTHY"
    CRITICAL = "CRITICAL"
    HOLLOWED = "HOLLOWED"
    RECOVERING = "RECOVERING"

class HealthRules:
    HP_RECOVERY_BY_DIFF = {
        "S": 25, "A": 20, "B": 18, "C": 20, 
        "D": 10, "E": 6, "F": 3,
    }

    @staticmethod
    def determine_status(current_hp: int, was_hollowed: bool = False) -> str:
        if current_hp <= 0:
            return HPStatus.HOLLOWED
            
        # If recovering from Hollowed, stay Recovering until healthy?
        # Legacy logic overrides status to RECOVERING if was_hollowed and > 0
        if was_hollowed:
            return HPStatus.RECOVERING
            
        if current_hp < 30:
            return HPStatus.CRITICAL
            
        return HPStatus.HEALTHY

    @staticmethod
    def calculate_recovery(difficulty: str) -> int:
        key = (difficulty or "E").upper()
        return HealthRules.HP_RECOVERY_BY_DIFF.get(key, 6)
