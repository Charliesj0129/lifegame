import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models.base import Base


class ActionLog(Base):
    __tablename__ = "action_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, ForeignKey("users.id"), index=True)

    action_text = Column(String, nullable=False)
    attribute_tag = Column(String, nullable=False)  # STR, INT...
    difficulty_tier = Column(String, nullable=False)  # F to S

    xp_gained = Column(Integer, default=0)
    gold_gained = Column(Integer, default=0)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())
