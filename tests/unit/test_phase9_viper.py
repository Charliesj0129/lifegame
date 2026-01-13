import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from legacy.services.narrative_service import narrative_service
from legacy.services.ai_engine import ai_engine


# Mock User and Rival classes
class MockUser:
    def __init__(self, id, level, hp=100, gold=100, streak_count=0):
        self.id = id
        self.level = level
        self.hp = hp
        self.gold = gold
        self.streak_count = streak_count
        self.max_hp = 100


class MockRival:
    def __init__(self, level):
        self.level = level


db_session = MagicMock(spec=AsyncSession)


@pytest.mark.asyncio
async def test_viper_hostile():
    """Test Hostile Logic: Low Level, Low Streak"""
    user_id = "u_hostile"
    # User Lv 1, Rival Lv 50, Streak 0 -> Gap > 10 -> Hostile

    # Mock Rival Fetch
    mock_rival = MockRival(level=50)

    with (
        patch("legacy.services.rival_service.rival_service.get_rival", new_callable=AsyncMock) as mock_get_rival,
        patch("legacy.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai,
    ):
        mock_get_rival.return_value = mock_rival
        mock_ai.return_value = {"comment": "You assume I care?"}

        context = {"user_level": 1, "streak": 0, "event": "Test Event"}

        await narrative_service.get_viper_comment(db_session, user_id, context)

        # Verify Prompt contains "Hostile"
        args, _ = mock_ai.call_args
        system_prompt = args[0]
        print(f"\n[Hostile Prompt]: {system_prompt}")
        assert "Hostile/Disappointed" in system_prompt


@pytest.mark.asyncio
async def test_viper_competitive():
    """Test Competitive Logic: Close Level"""
    user_id = "u_comp"
    # User Lv 10, Rival Lv 12, Streak 3 -> Gap 2 -> Competitive

    mock_rival = MockRival(level=12)

    with (
        patch("legacy.services.rival_service.rival_service.get_rival", new_callable=AsyncMock) as mock_get_rival,
        patch("legacy.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai,
    ):
        mock_get_rival.return_value = mock_rival
        mock_ai.return_value = {"comment": "Catch me if you can."}

        context = {"user_level": 10, "streak": 3, "event": "Test Event"}

        await narrative_service.get_viper_comment(db_session, user_id, context)

        args, _ = mock_ai.call_args
        system_prompt = args[0]
        print(f"\n[Competitive Prompt]: {system_prompt}")
        assert "Competitive" in system_prompt


@pytest.mark.asyncio
async def test_viper_respectful():
    """Test Respectful Logic: High Streak, Close Level"""
    user_id = "u_respect"
    # User Lv 48, Rival Lv 50, Streak 10 -> Gap 2, Streak > 5 -> Respectful

    mock_rival = MockRival(level=50)

    with (
        patch("legacy.services.rival_service.rival_service.get_rival", new_callable=AsyncMock) as mock_get_rival,
        patch("legacy.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai,
    ):
        mock_get_rival.return_value = mock_rival
        mock_ai.return_value = {"comment": "Not bad."}

        context = {"user_level": 48, "streak": 10, "event": "Test Event"}

        await narrative_service.get_viper_comment(db_session, user_id, context)

        args, _ = mock_ai.call_args
        system_prompt = args[0]
        print(f"\n[Respectful Prompt]: {system_prompt}")
        assert "Respectful Rival" in system_prompt
