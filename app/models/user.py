from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)  # Line User ID
    name = Column(String, nullable=True)

    # Progression
    level = Column(Integer, default=1)

    # Attributes
    str = Column(Integer, default=1)
    vit = Column(Integer, default=1)
    int = Column(Integer, default=1)
    wis = Column(Integer, default=1)
    cha = Column(Integer, default=1)

    # Currencies
    xp = Column(Integer, default=0)  # Total collected XP maybe? Or per level?
    # Let's simple accumulate XP per attribute later, but for now simple global XP or per attribute?
    # PRD says "XP determines Level". Rules says "Level = (Sum Attributes)/5".
    # So XP might be just a log or we track XP per attribute.
    # To keep it simple M1: Track raw Attribute values.
    # Actions give XP which converts to Attribute Points?
    # Or Actions directly give Attribute Points?
    # "Action -> XP Calculation". "Attributes feed specific attributes".
    # Let's assume Actions give XP towards specific Attributes.
    # So we need xp_str, xp_vit etc?
    # For M1, let's stick to the Plan: User has STR, INT values.
    # We can add `xp_str`, `xp_int` later if we need fine grained bars.
    # For now, let's assume we just increment the Attribute value directly for simplicity or store fractional?
    # Actually, usually you earn XP, then Level Up Attribute.
    # Let's add xp_* columns to be safe for "Bar" visualization.

    str_xp = Column(Integer, default=0)
    vit_xp = Column(Integer, default=0)
    int_xp = Column(Integer, default=0)
    wis_xp = Column(Integer, default=0)
    cha_xp = Column(Integer, default=0)

    gold = Column(Integer, default=0)
    penalty_pending = Column(Boolean, default=False)

    # Push preferences
    push_enabled = Column(Boolean, default=True)
    push_timezone = Column(String, default="Asia/Taipei")
    push_times = Column(
        JSON,
        default=lambda: {"morning": "08:00", "midday": "12:30", "night": "21:00"},
    )

    # Vital Stats
    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    is_hollowed = Column(Boolean, default=False)
    hp_status = Column(String, default="HEALTHY")  # HEALTHY, CRITICAL, HOLLOWED, RECOVERING
    hollowed_at = Column(DateTime(timezone=True), nullable=True)
    talent_points = Column(Integer, default=3, nullable=False)

    # M6: Habit Streaks
    settings = Column(
        JSON,
        default=lambda: {"theme": "cyberpunk", "notifications": True, "language": "zh-TW"},
    )
    streak_count = Column(Integer, default=0)
    last_active_date = Column(DateTime(timezone=True), nullable=True)  # Tracks the *day* of last activity

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
