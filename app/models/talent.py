from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, JSON
import sqlalchemy
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import text
from app.models.base import Base
import enum
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User


class ClassType(str, enum.Enum):
    WARLORD = "WARLORD"
    ALCHEMIST = "ALCHEMIST"
    SHADOW = "SHADOW"


class EffectType(str, enum.Enum):
    XP_GAIN = "XP_GAIN"
    GOLD_GAIN = "GOLD_GAIN"
    HP_DRAIN_REDUCE = "HP_DRAIN_REDUCE"
    EVASION = "EVASION"


INITIAL_TALENTS = [
    # Warlord Tree (STR)
    {
        "id": "STR_01_BLOODLUST",
        "class_type": ClassType.WARLORD,
        "tier": 1,
        "name": "Bloodlust",
        "name_zh": "嗜血",
        "description": "+5% XP per streak day",
        "effect_meta": {"attr": "xp_gain", "val": 0.05, "type": "streak"},
    },
    {
        "id": "STR_02_IRON_WILL",
        "class_type": ClassType.WARLORD,
        "tier": 2,
        "name": "Iron Will",
        "name_zh": "鋼鐵意志",
        "description": "-10% HP drain",
        "effect_meta": {"attr": "hp_drain", "val": -0.1},
        "parent_id": "STR_01_BLOODLUST",
    },
    {
        "id": "STR_03_BERSERKER",
        "class_type": ClassType.WARLORD,
        "tier": 3,
        "name": "Berserker",
        "name_zh": "狂暴",
        "description": "+25% XP when HP<30%",
        "effect_meta": {"attr": "xp_critical", "val": 0.25},
        "parent_id": "STR_02_IRON_WILL",
    },
    # Alchemist Tree (INT)
    {
        "id": "INT_01_INSIGHT",
        "class_type": ClassType.ALCHEMIST,
        "tier": 1,
        "name": "Insight",
        "name_zh": "洞察",
        "description": "+10% Gold",
        "effect_meta": {"attr": "gold_gain", "val": 0.1},
    },
    {
        "id": "INT_02_TRANSMUTE",
        "class_type": ClassType.ALCHEMIST,
        "tier": 2,
        "name": "Transmute",
        "name_zh": "煉金",
        "description": "Convert junk to gold",
        "effect_meta": {"attr": "transmute", "val": 1},
        "parent_id": "INT_01_INSIGHT",
    },
    {
        "id": "INT_03_PHILOSOPHER",
        "class_type": ClassType.ALCHEMIST,
        "tier": 3,
        "name": "Philosopher",
        "name_zh": "智者",
        "description": "Double craft chance",
        "effect_meta": {"attr": "craft_bonus", "val": 2.0},
        "parent_id": "INT_02_TRANSMUTE",
    },
    # Shadow Tree (LCK)
    {
        "id": "LCK_01_EVASION",
        "class_type": ClassType.SHADOW,
        "tier": 1,
        "name": "Evasion",
        "name_zh": "閃避",
        "description": "20% chance evade penalty",
        "effect_meta": {"attr": "evasion", "val": 0.2},
    },
    {
        "id": "LCK_02_GHOST",
        "class_type": ClassType.SHADOW,
        "tier": 2,
        "name": "Ghost",
        "name_zh": "幽靈",
        "description": "Hide from rival",
        "effect_meta": {"attr": "rival_hide", "val": 1},
        "parent_id": "LCK_01_EVASION",
    },
    {
        "id": "LCK_03_MASTER",
        "class_type": ClassType.SHADOW,
        "tier": 3,
        "name": "Shadow Master",
        "name_zh": "影行者",
        "description": "Double loot chance",
        "effect_meta": {"attr": "loot_bonus", "val": 2.0},
        "parent_id": "LCK_02_GHOST",
    },
]


class TalentTree(Base):
    __tablename__ = "talent_trees"

    id = Column(String, primary_key=True)
    class_type = Column(String, nullable=False)  # e.g. "GENERAL", "WARRIOR", "HACKER"
    tier = Column(Integer, default=1)
    name = Column(String, nullable=False)
    name_zh = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    description_zh = Column(Text, nullable=True)
    effect_meta = Column(JSON, nullable=False)  # {"attr": "str", "val": 1}
    parent_id = Column(String, ForeignKey("talent_trees.id"), nullable=True)
    max_rank = Column(Integer, default=1)
    cost = Column(Integer, default=1)

    # Relationships
    children: Mapped[List["TalentTree"]] = relationship(
        "TalentTree", backref=sqlalchemy.orm.backref("parent", remote_side=[id])
    )


class UserTalent(Base):
    __tablename__ = "user_talents"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    talent_id = Column(String, ForeignKey("talent_trees.id"), nullable=False)
    current_rank = Column(Integer, default=1)
    is_active = Column(Boolean, server_default=text("TRUE"))

    # Relationships
    # Relationships
    user: Mapped["User"] = relationship("User", backref="talents")
    talent: Mapped["TalentTree"] = relationship("TalentTree")
