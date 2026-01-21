import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class ItemRarity(str, enum.Enum):
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"


class ItemType(str, enum.Enum):
    CONSUMABLE = "CONSUMABLE"  # Buffs, Potions
    REWARD = "REWARD"  # O2O Coupons
    KEY = "KEY"  # Unique Unlocks


class Item(Base):
    __tablename__ = "items"

    id = Column(String, primary_key=True)  # e.g. "POTION_FOCUS_S"
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    rarity = Column(Enum(ItemRarity), default=ItemRarity.COMMON)
    type = Column(Enum(ItemType), default=ItemType.CONSUMABLE)
    price = Column(Integer, default=100)
    is_purchasable = Column(Boolean, default=False)

    # JSON for flexibility: {"buff": "INT", "multiplier": 1.2, "duration_minutes": 60}
    effect_meta = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserItem(Base):
    __tablename__ = "user_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True)
    item_id = Column(String, ForeignKey("items.id"))

    quantity = Column(Integer, default=1)
    acquired_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", backref="inventory")
    item: Mapped["Item"] = relationship("Item")


class UserBuff(Base):
    __tablename__ = "user_buffs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True)

    # e.g. "INT" or "ALL" or "XP"
    target_attribute = Column(String, nullable=False)
    multiplier = Column(Float, default=1.0)

    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", backref="buffs")


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(String, primary_key=True)  # e.g. "MEGA_POTION_RECIPE"
    name = Column(String, nullable=False)
    result_item_id = Column(String, ForeignKey("items.id"), nullable=False)
    result_quantity = Column(Integer, default=1)
    success_rate = Column(Float, default=1.0)

    # Relationships
    # Relationships
    result_item: Mapped["Item"] = relationship("Item")
    ingredients: Mapped[list["RecipeIngredient"]] = relationship("RecipeIngredient", backref="recipe")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(String, ForeignKey("recipes.id"), index=True)
    item_id = Column(String, ForeignKey("items.id"))
    quantity_required = Column(Integer, default=1)

    item: Mapped["Item"] = relationship("Item")


class BossStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DEFEATED = "DEFEATED"
    ESCAPED = "ESCAPED"


class Boss(Base):
    __tablename__ = "bosses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True)

    name = Column(String, nullable=False)
    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    level = Column(Integer, default=1)
    status = Column(Enum(BossStatus), default=BossStatus.ACTIVE)

    deadline = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    # Relationships
    user: Mapped["User"] = relationship("User", backref="bosses")


class UserPIDState(Base):
    __tablename__ = "user_pid_states"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    integral = Column(Float, default=0.0)
    last_error = Column(Float, default=0.0)
    error_history = Column(JSON, default=list)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", backref="pid_state")
