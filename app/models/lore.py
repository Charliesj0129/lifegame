import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.models.base import Base


class LoreEntry(Base):
    __tablename__ = "lore_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    series = Column(String, nullable=False)
    chapter = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LoreProgress(Base):
    __tablename__ = "lore_progress"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    series = Column(String, nullable=False)
    current_chapter = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
