from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from app.models.base import Base
import enum


class DungeonStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"


class DungeonType(str, enum.Enum):
    FOCUS = "FOCUS"
    WRITING = "WRITING"
    CODING = "CODING"
    MEDITATION = "MEDITATION"
    RESCUE = "RESCUE"


DUNGEON_TEMPLATES = {
    DungeonType.FOCUS.value: {
        "name": "專注深域",
        "duration_minutes": 60,
        "xp_reward": 100,
        "stages": [
            {"title": "熱身：列出目標", "desc": "確認今日的關鍵任務。"},
            {"title": "深度專注：25 分鐘", "desc": "停止干擾，進入專注。"},
            {"title": "回顧：寫下成果", "desc": "簡短記錄完成內容。"},
        ],
    },
    DungeonType.WRITING.value: {
        "name": "寫作深淵",
        "duration_minutes": 90,
        "xp_reward": 150,
        "stages": [
            {"title": "預備：整理大綱", "desc": "列出 3 個要點。"},
            {"title": "輸出：連續寫作 45 分鐘", "desc": "不中斷輸出。"},
            {"title": "收束：修正 10 分鐘", "desc": "快速潤飾內容。"},
        ],
    },
    DungeonType.CODING.value: {
        "name": "程式迷宮",
        "duration_minutes": 90,
        "xp_reward": 150,
        "stages": [
            {"title": "熱身：讀需求", "desc": "寫下 2 個驗收條件。"},
            {"title": "開發：完成核心功能", "desc": "集中實作。"},
            {"title": "驗收：跑一輪測試", "desc": "確保功能通過。"},
        ],
    },
    DungeonType.MEDITATION.value: {
        "name": "靜心之境",
        "duration_minutes": 30,
        "xp_reward": 60,
        "stages": [
            {"title": "呼吸：1 分鐘", "desc": "觀察呼吸。"},
            {"title": "放空：5 分鐘", "desc": "保持專注。"},
        ],
    },
    DungeonType.RESCUE.value: {
        "name": "救援協定",
        "duration_minutes": 30,
        "xp_reward": 30,
        "stages": [
            {"title": "呼吸：深呼吸 5 次", "desc": "降低焦躁。"},
            {"title": "補水：喝一杯水", "desc": "補充體力。"},
            {"title": "行動：完成一件小事", "desc": "重新啟動。"},
        ],
    },
}


class Dungeon(Base):
    __tablename__ = "dungeons"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    dungeon_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    duration_minutes = Column(Integer, default=60)
    status = Column(String, server_default="ACTIVE")
    deadline = Column(DateTime(timezone=True), nullable=True)
    xp_reward = Column(Integer, default=100)
    reward_claimed = Column(Boolean, server_default=text("FALSE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    stages = relationship(
        "DungeonStage", backref="dungeon", order_by="DungeonStage.order"
    )


class DungeonStage(Base):
    __tablename__ = "dungeon_stages"

    id = Column(String, primary_key=True)
    dungeon_id = Column(String, ForeignKey("dungeons.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    order = Column(Integer, default=1)
    is_complete = Column(Boolean, server_default=text("FALSE"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
