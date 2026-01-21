"""
驗證系統單元測試
Tests for Phase 8: Multi-Modal Verification (The Arbiter)
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.quest import Quest, QuestStatus
from app.models.user import User
from application.services.verification_service import Verdict, verification_service


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create test user
        user = User(id="test_verify_user", name="Tester", xp=100)
        session.add(user)

        # Create verifiable quest (TEXT type)
        text_quest = Quest(
            id="QUEST_TEXT_001",
            user_id="test_verify_user",
            title="晨跑 5 公里",
            description="早起跑步",
            status=QuestStatus.ACTIVE.value,
            xp_reward=50,
            verification_type="TEXT",
            verification_keywords=["跑步", "晨跑", "公里", "running"],
        )
        session.add(text_quest)

        # Create verifiable quest (IMAGE type)
        image_quest = Quest(
            id="QUEST_IMAGE_001",
            user_id="test_verify_user",
            title="去健身房運動",
            description="拍照證明",
            status=QuestStatus.ACTIVE.value,
            xp_reward=80,
            verification_type="IMAGE",
            verification_keywords=["gym", "健身房", "運動", "weights", "treadmill"],
        )
        session.add(image_quest)

        # Create verifiable quest (LOCATION type)
        location_quest = Quest(
            id="QUEST_LOC_001",
            user_id="test_verify_user",
            title="到公司打卡",
            description="GPS 驗證",
            status=QuestStatus.ACTIVE.value,
            xp_reward=30,
            verification_type="LOCATION",
            verification_keywords=[],
            location_target={"lat": 25.033, "lng": 121.565, "radius_m": 100},
        )
        session.add(location_quest)

        await session.commit()
        yield session


@pytest.mark.asyncio
async def test_get_verifiable_quests(db_session):
    """Test fetching verifiable quests."""
    quests = await verification_service.get_verifiable_quests(db_session, "test_verify_user")

    assert len(quests) == 3
    types = {q.verification_type for q in quests}
    assert types == {"TEXT", "IMAGE", "LOCATION"}


@pytest.mark.asyncio
async def test_auto_match_quest_text(db_session):
    """Test auto-matching text content to quest."""
    quest = await verification_service.auto_match_quest(db_session, "test_verify_user", "我今天早上跑步了", "TEXT")

    assert quest is not None
    assert quest.id == "QUEST_TEXT_001"


@pytest.mark.asyncio
async def test_auto_match_quest_image(db_session):
    """Test auto-matching image to IMAGE type quest."""
    quest = await verification_service.auto_match_quest(db_session, "test_verify_user", b"fake_image_bytes", "IMAGE")

    assert quest is not None
    assert quest.verification_type == "IMAGE"


@pytest.mark.asyncio
async def test_verify_location_approved(db_session):
    """Test location verification within radius."""
    from sqlalchemy import select

    quest = (await db_session.execute(select(Quest).where(Quest.id == "QUEST_LOC_001"))).scalar_one()

    # Location within 100m radius
    result = await verification_service.verify_location(db_session, quest, 25.033, 121.565)

    assert result["verdict"] == Verdict.APPROVED
    assert result["meta"]["distance_m"] < 100


@pytest.mark.asyncio
async def test_verify_location_rejected(db_session):
    """Test location verification outside radius."""
    from sqlalchemy import select

    quest = (await db_session.execute(select(Quest).where(Quest.id == "QUEST_LOC_001"))).scalar_one()

    # Location far away (Taipei vs Kaohsiung)
    result = await verification_service.verify_location(db_session, quest, 22.627, 120.301)

    assert result["verdict"] == Verdict.REJECTED
    assert result["meta"]["distance_m"] > 200000  # More than 200km


@pytest.mark.asyncio
async def test_verify_text_with_mock_ai(db_session):
    """Test text verification with mocked AI response."""
    from sqlalchemy import select

    quest = (await db_session.execute(select(Quest).where(Quest.id == "QUEST_TEXT_001"))).scalar_one()

    mock_response = {
        "verdict": "APPROVED",
        "reason": "使用者提到跑步完成",
        "follow_up": None,
        "detected_labels": ["跑步", "運動"],
    }

    with patch("application.services.ai_engine.ai_engine.verify_multimodal", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = mock_response

        result = await verification_service.verify_text(db_session, quest, "我剛跑完 5 公里，流了一身汗")

        assert result["verdict"] == Verdict.APPROVED
        assert "跑步" in result["reason"]


@pytest.mark.asyncio
async def test_verify_image_with_mock_ai(db_session):
    """Test image verification with mocked AI response."""
    from sqlalchemy import select

    quest = (await db_session.execute(select(Quest).where(Quest.id == "QUEST_IMAGE_001"))).scalar_one()

    mock_response = {
        "verdict": "APPROVED",
        "reason": "圖片顯示健身房環境",
        "detected_labels": ["gym", "weights", "treadmill"],
    }

    with patch("application.services.ai_engine.ai_engine.verify_multimodal", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = mock_response

        result = await verification_service.verify_image(db_session, quest, b"fake_gym_image_bytes")

        assert result["verdict"] == Verdict.APPROVED
        assert "gym" in result["meta"]["labels"]


@pytest.mark.asyncio
async def test_process_verification_no_quest(db_session):
    """Test verification when no matching quest exists."""
    response = await verification_service.process_verification(db_session, "nonexistent_user", "some text", "TEXT")

    assert response["quest"] is None
    assert response["verdict"] == Verdict.UNCERTAIN
    assert "無" in response["message"] or "找不到" in response["message"]


@pytest.mark.asyncio
async def test_haversine_distance():
    """Test haversine distance calculation."""
    # Taipei 101 to Taipei Main Station (~5km)
    distance = verification_service._haversine(
        25.0339,
        121.5645,
        25.0478,
        121.5170,  # Taipei 101  # Taipei Main Station
    )

    assert 4000 < distance < 6000  # Approximately 5km
