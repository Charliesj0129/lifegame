import yaml
from pathlib import Path
from math import floor
from app.models.user import User

# Load Rules
RULES_PATH = Path("doc/rules_of_the_world.md")

class AccountantService:
    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self):
        try:
            with open(RULES_PATH, "r") as f:
                content = f.read()
                # Parse Frontmatter
                _, frontmatter, _ = content.split("---", 2)
                return yaml.safe_load(frontmatter)
        except Exception:
            # Fallback default rules if file missing or parse error
            return {
                "difficulty_tiers": {
                    "F": {"multiplier": 0.5},
                    "E": {"multiplier": 1.0},
                    "D": {"multiplier": 2.0},
                    "C": {"multiplier": 5.0},
                    "B": {"multiplier": 10.0},
                    "A": {"multiplier": 50.0}
                },
                "game_loop": {"drop_rate_base": 0.2}
            }

    def calculate_xp(self, attribute_tag: str, difficulty: str) -> int:
        base_xp = 100 # From design (Lv 1-10: 100 * Level, but per action base?)
        # Rules say: "Action -> Validation -> XP". 
        # XP Curve table says "Level 1 -> 2 needs 100 XP". 
        # Let's assume Base XP for an "E" (Easy) task is enough to make progress?
        # If "Easy" = 1.0x.
        # Let's define Base XP per action = 10 (so 10 Easy actions to level up? Or 1?)
        # "Levels 1-10 are fast (daily level up)".
        # If "Daily Cap" is 5000.
        # Let's set Base XP = 50.
        base_xp = 50
        
        tier = self.rules["difficulty_tiers"].get(difficulty, {"multiplier": 1.0})
        multiplier = tier["multiplier"]
        
        return int(base_xp * multiplier)

    def apply_xp(self, user: User, attribute: str, xp_amount: int):
        # Update specific attribute XP (if we tracked it) or just raw value?
        # Plan says "users table... str/int... default 1".
        # Let's assume we increment the attribute *value* directly? 
        # No, typically you gain XP, then stat goes up.
        # But for M1 MVP, let's keep it simple: "Action of Type INT adds to INT score". 
        # Let's verify standard RPG. Usually XP is global, Stats are manual. 
        # OR usage-based: Skyrim. "Use sword -> Sword skill up".
        # Lifgame concept: "Coding -> INT up".
        # So we likely need "INT XP".
        # Schema has `int_xp` etc.
        
        attr_key = attribute.lower()
        if hasattr(user, f"{attr_key}_xp"):
             current_xp = getattr(user, f"{attr_key}_xp")
             setattr(user, f"{attr_key}_xp", current_xp + xp_amount)
             
             # Check for Stat Level Up?
             # Simple logic: Stat Level = sqrt(XP) or linear?
             # Let's just store XP for now. Derived Stat Level can be calculated.
             # Or User.str is the level.
             # Let's imply: 100 XP = +1 Stat Level?
             # Let's do: Every 100 XP in a stat -> +1 to that Stat.
             
             new_xp = current_xp + xp_amount
             
             # Calculate Stat Level
             # Base=1. Cost to upgrade? 
             # Let's keep it simple: Stat Level = 1 + floor(XP / 100).
             new_stat_level = 1 + floor(new_xp / 100)
             setattr(user, attr_key, new_stat_level)
             
        # Update Global Level
        # Level = Average of (STR, INT, VIT, WIS, CHA)
        s = user.str or 1
        i = user.int or 1
        v = user.vit or 1
        w = user.wis or 1
        c = user.cha or 1
        
        total_msg = s + i + v + w + c
        user.level = floor(total_msg / 5)

    def apply_buffs(self, xp_amount: int, buffs: list, attribute: str) -> int:
        multiplier = 1.0
        for buff in buffs:
            if buff.target_attribute == "ALL" or buff.target_attribute.upper() == attribute.upper():
                multiplier *= float(buff.multiplier or 1.0)
        
        return int(xp_amount * multiplier)

accountant = AccountantService()
