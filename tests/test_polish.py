import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.verification_service import verification_service, Verdict
from app.services.user_service import user_service
from app.services.quest_service import quest_service
from app.models.quest import Quest
from app.models.user import User
from app.models.dda import HabitState


@pytest.mark.asyncio
async def test_verification_service_standardization():
    # Mock AI Engine
    with patch("app.services.verification_service.ai_engine") as mock_ai:
        mock_ai.verify_multimodal = AsyncMock(
            return_value={
                "verdict": "APPROVED",
                "reason": "Clear evidence.",
                "detected_labels": [],
            }
        )

        # Mock Session & Service Dependencies
        mock_session = AsyncMock()
        quest = Quest(
            id="q1",
            title="Run 5k",
            verification_type="TEXT",
            verification_keywords=["run", "5k"],
            xp_reward=100,
        )

        # Test verify_text
        result = await verification_service.verify_text(
            mock_session, quest, "I ran 5k today"
        )
        assert result["verdict"] == Verdict.APPROVED
        assert result["reason"] == "Clear evidence."

        # Test process_verification success flow
        with (
            patch.object(verification_service, "auto_match_quest", return_value=quest),
            patch.object(
                verification_service,
                "_complete_quest",
                return_value={"xp": 10, "gold": 0, "story": "Mission Complete"},
            ),
        ):

            response = await verification_service.process_verification(
                mock_session, "u1", "I ran 5k", "TEXT"
            )
            assert response["verdict"] == Verdict.APPROVED
            assert "Mission Complete" in response["message"]


@pytest.mark.asyncio
async def test_user_service_habit_update():
    # Mock Session and AI
    mock_session = AsyncMock()
    with (
        patch("app.services.user_service.ai_engine") as mock_ai,
        patch("app.services.user_service.accountant"),
        patch("app.services.user_service.inventory_service") as mock_inv,
        patch("app.services.user_service.loot_service") as mock_loot,
    ):

        mock_ai.analyze_action = AsyncMock(
            return_value={
                "stat_type": "STR",
                "difficulty_tier": "C",
                "narrative": "Good job.",
            }
        )

        # Explicit AsyncMocks for service calls
        mock_inv.get_active_buffs = AsyncMock(return_value=[])
        mock_loot.calculate_drop = AsyncMock(return_value=None)

        # Mock User (Initialize attrs to avoid Pydantic ValidationError)
        user = User(id="u1", level=1, xp=0, str=10, int=10, vit=10, wis=10, cha=10)
        # Mock Habit
        habit = HabitState(user_id="u1", habit_tag="gym", ema_p=0.5, tier="T1")

        # Mock session.add to be synchronous
        mock_session.add = MagicMock()

        # Setup DB Returns - Explicit MagicMock for Result
        mock_result_user = MagicMock()
        mock_result_user.scalars.return_value.first.return_value = user

        mock_result_habits = MagicMock()
        mock_result_habits.scalars.return_value.all.return_value = [habit]

        # side_effect to return different results
        # 1. get_user -> active_buffs(inv) -> get_habits(dda) -> streak logic ...
        # process_action calls:
        #   1. get_or_create_user (exec calls)
        #   2. ...
        #   3. get_active_buffs (inv service, no session exec?)
        #   4. session.add(log)
        #   5. fetch habits (session exec)
        #   6. unlock_next_chapter (if level up)

        # Note: inventory_service.get_active_buffs might call session.execute?
        # But we mocked the service method directly, so it won't use session.
        # So logic is:
        # Call 1: get_or_create_user -> select(User)
        # Call 2: select(HabitState)

        mock_session.execute.side_effect = [
            mock_result_user,
            mock_result_habits,
            MagicMock(),
        ]

        # Run process_action
        result = await user_service.process_action(
            mock_session, "u1", "I went to the gym"
        )

        # Assert Habit Updated
        # EMA: 0.5 * 0.8 + 1.0 * 0.2 = 0.4 + 0.2 = 0.6
        assert round(habit.ema_p, 2) == 0.6
        # Tier: 0.6 >= 0.5 -> T2
        assert habit.tier == "T2"
        assert "習慣[gym]" in result.text


@pytest.mark.asyncio
async def test_quest_service_dda_push():
    mock_session = AsyncMock()
    # Mock session.add
    mock_session.add = MagicMock()

    # Patch dependencies imported INSIDE the function
    with (
        patch("app.services.quest_service.ai_engine") as mock_ai,
        patch("app.services.user_service.user_service") as mock_user_svc,
        patch("app.services.rival_service.rival_service") as mock_rival_svc,
    ):

        mock_ai.generate_json = AsyncMock(
            return_value=[
                {"title": "晨間慢跑", "desc": "慢跑 10 分鐘", "diff": "D", "xp": 20}
            ]
        )

        # Mock User Service
        mock_user = MagicMock(hp=100, level=5)
        mock_user_svc.get_user = AsyncMock(return_value=mock_user)

        # Mock Rival Service
        mock_rival = MagicMock(level=1)
        mock_rival_svc.get_rival = AsyncMock(return_value=mock_rival)

        # Mock existing quests (Empty)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        quests = await quest_service.trigger_push_quests(mock_session, "u1", "Morning")

        assert len(quests) == 3
        assert quests[0].title == "晨間慢跑"
