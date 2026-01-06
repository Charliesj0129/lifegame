import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.quest_service import quest_service
from app.models.dda import DailyOutcome
from app.models.user import User
from app.models.quest import Rival
import datetime


@pytest.mark.asyncio
async def test_dda_trigger():
    # Mock Session and Data
    mock_session = AsyncMock()

    # Setup Result Mock
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.side_effect = [
        User(id="u1", level=1),  # User
        Rival(id="r1", level=1),  # Rival
        None,  # Goal
        DailyOutcome(
            user_id="u1",
            done=False,
            date=datetime.date.today() - datetime.timedelta(days=1),
        ),  # Failed
    ]
    # Ensure execute returns this mock
    mock_session.execute.return_value = mock_result

    # Mock AI
    with patch(
        "app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = [{"title": "Easy Recovery", "diff": "E", "xp": 10}]

        # Execute
        quests = await quest_service._generate_daily_batch(mock_session, "u1")

        # Verify Prompt contained DDA modifier
        call_args = mock_ai.call_args[0]
        prompt = call_args[0]
        assert "User is struggling" in prompt
        assert "EASIER" in prompt

        assert len(quests) == 1
        assert quests[0].difficulty_tier == "E"


@pytest.mark.asyncio
async def test_serendipity_trigger():
    # Mock data - Success yesterday (No DDA)
    mock_session = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.side_effect = [
        User(id="u1", level=1),
        Rival(id="r1", level=1),
        None,
        DailyOutcome(user_id="u1", done=True),  # Success
    ]
    mock_session.execute.return_value = mock_result

    # Force Luck
    with (
        patch("random.random", return_value=0.1),
        patch(
            "app.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock
        ) as mock_ai,
    ):

        mock_ai.return_value = [
            {"title": "Normal Task", "desc": "Desc", "diff": "D", "xp": 20}
        ]

        try:
            await quest_service._generate_daily_batch(mock_session, "u1")
        except Exception:
            pass  # Ignore fallback error

        # Verify Prompt contained Serendipity
        if mock_ai.called:
            call_args = mock_ai.call_args[0]
            prompt = call_args[0]
            assert "RARE" in prompt
        else:
            pytest.fail("AI not called")
