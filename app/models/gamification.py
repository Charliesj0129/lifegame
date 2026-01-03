from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.models.base import Base

class ItemRarity(str, enum.Enum):
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"

class ItemType(str, enum.Enum):
    CONSUMABLE = "CONSUMABLE"  # Buffs, Potions
    REWARD = "REWARD"      # O2O Coupons
    KEY = "KEY"            # Unique Unlocks
    
class Item(Base):
    __tablename__ = "items"
    
    id = Column(String, primary_key=True) # e.g. "POTION_FOCUS_S"
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    rarity = Column(Enum(ItemRarity), default=ItemRarity.COMMON)
    type = Column(Enum(ItemType), default=ItemType.CONSUMABLE)
    
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
    user = relationship("User", backref="inventory")
    item = relationship("Item")

class UserBuff(Base):
    __tablename__ = "user_buffs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True)
    
    # e.g. "INT" or "ALL" or "XP"
    target_attribute = Column(String, nullable=False) 
    multiplier = Column(Float, default=1.0)
    
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", backref="buffs")
