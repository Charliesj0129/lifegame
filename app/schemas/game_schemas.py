from pydantic import BaseModel
from typing import Optional, Any
from app.models.gamification import Item

class ProcessResult(BaseModel):
    text: str # Fallback text
    user_id: str
    action_text: str
    attribute: str
    difficulty_tier: str = "E"
    xp_gained: int
    new_level: int
    leveled_up: bool
    loot_drop: Optional[Any] = None # Pydantic might struggle with SQLAlchemy object, use dict or schema?
    # For now, let's store keys needed for rendering
    loot_name: Optional[str] = None
    loot_rarity: Optional[str] = None
    narrative: Optional[str] = None
    
    current_attributes: dict[str, int]
    current_xp: int
    next_level_xp: int = 100 
    
    # M6 Gamification
    streak_count: int = 0
    user_title: str = "Runner"
    
    def to_text_message(self) -> str:
        msg = self.text
        if self.loot_name:
            rarity = self.loot_rarity or ""
            msg += f"\n🎁 掉落：獲得 {self.loot_name}（{rarity}）"
        return msg
