from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    JSON,
    ForeignKey,
    Date,
    DateTime,
)
from sqlalchemy.sql import func
import uuid
import enum
from app.models.base import Base


class GoalStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class QuestType(str, enum.Enum):
    MAIN = "MAIN"
    SIDE = "SIDE"
    REDEMPTION = "REDEMPTION"


class QuestStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DONE = "DONE"
    FAILED = "FAILED"


class Goal(Base):
    __tablename__ = "goals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default=GoalStatus.ACTIVE.value)  # Use String for broader compatibility (sqlite)
    decomposition_json = Column(JSON, nullable=True)  # Stores the raw AI plan
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Quest(Base):
    __tablename__ = "quests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    goal_id = Column(String, ForeignKey("goals.id"), nullable=True)  # Can have standalone quests
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    difficulty_tier = Column(String, nullable=True)  # F to S

    quest_type = Column(String, default=QuestType.MAIN.value)
    status = Column(String, default=QuestStatus.PENDING.value)

    xp_reward = Column(Integer, default=0)
    scheduled_date = Column(Date, nullable=True)  # Target Date

    is_redemption = Column(Boolean, default=False)

    # Verification (optional)
    verification_type = Column(String, nullable=True)  # TEXT | IMAGE | LOCATION
    verification_keywords = Column(JSON, nullable=True)  # list[str]
    location_target = Column(JSON, nullable=True)  # {"lat": float, "lng": float, "radius_m": int}

    meta = Column(JSON, nullable=True)  # Generic metadata (e.g. graph_node_id)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Rival(Base):
    __tablename__ = "rivals"

    id = Column(String, primary_key=True, default="VIPER")
    user_id = Column(
        String, ForeignKey("users.id"), nullable=False
    )  # Each user has their own instance of Viper? Or global? Assuming per user for now.

    name = Column(String, default="Viper")
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)

    last_updated = Column(DateTime(timezone=True), server_default=func.now())
