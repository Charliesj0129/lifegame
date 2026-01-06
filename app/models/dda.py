import datetime
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, JSON, Float, Date
from sqlalchemy.sql import func, text
from app.models.base import Base


class HabitState(Base):
    __tablename__ = "habit_states"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # New DDA fields
    habit_tag = Column(String, nullable=True)
    habit_name = Column(String, nullable=True)  # legacy/alias
    tier = Column(String, default="T1")
    ema_p = Column(Float, default=0.6)
    last_zone = Column(String, default="YELLOW")
    zone_streak_days = Column(Integer, default=0)
    last_outcome_date = Column(Date, nullable=True)

    # Legacy fields kept for compatibility
    current_tier = Column(Integer, nullable=True)
    exp = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DailyOutcome(Base):
    __tablename__ = "daily_outcomes"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    habit_tag = Column(String, nullable=True)
    date = Column(Date, default=datetime.date.today)
    done = Column(Boolean, server_default=text("FALSE"), default=False, nullable=False)
    is_global = Column(Boolean, server_default=text("FALSE"), default=False, nullable=False)
    rescue_used = Column(Boolean, server_default=text("FALSE"), default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CompletionLog(Base):
    __tablename__ = "completion_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    quest_id = Column(String, nullable=True)
    habit_tag = Column(String, nullable=True)
    tier_used = Column(String, nullable=True)
    source = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())


class PushProfile(Base):
    __tablename__ = "push_profiles"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    morning_time = Column(String, default="08:00")
    midday_time = Column(String, default="12:30")
    night_time = Column(String, default="21:30")
    quiet_hours = Column(JSON, nullable=True)

    last_morning_date = Column(Date, nullable=True)
    last_midday_date = Column(Date, nullable=True)
    last_night_date = Column(Date, nullable=True)

    # Legacy field
    preferred_time = Column(String, default="09:00")
