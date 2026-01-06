"""
Tests for DDA Scheduler
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.scheduler import DDAScheduler


class TestDDAScheduler:
    """Tests for the DDA Scheduler service."""

    def test_scheduler_initializes(self):
        """Verify scheduler can be created without errors."""
        scheduler = DDAScheduler()
        assert scheduler._is_running is False
        assert scheduler.scheduler is not None

    @pytest.mark.asyncio
    async def test_scheduler_starts_and_stops(self):
        """Verify scheduler can start and stop cleanly."""
        scheduler = DDAScheduler()

        # Start
        scheduler.start()
        assert scheduler._is_running is True

        # Double start should warn but not fail
        scheduler.start()
        assert scheduler._is_running is True

        # Shutdown
        scheduler.shutdown()
        assert scheduler._is_running is False

        # Double shutdown should be safe
        scheduler.shutdown()
        assert scheduler._is_running is False

    @pytest.mark.asyncio
    async def test_scheduler_has_correct_jobs(self):
        """Verify all three jobs are registered."""
        scheduler = DDAScheduler()
        scheduler.start()

        try:
            jobs = scheduler.scheduler.get_jobs()
            job_ids = {job.id for job in jobs}

            assert "push_tick" in job_ids
        finally:
            scheduler.shutdown()


@pytest.mark.asyncio
async def test_morning_push_calls_quest_service():
    """Verify morning push logic triggers quest generation."""
    scheduler = DDAScheduler()

    with (
        patch("app.services.scheduler.quest_service") as mock_quest_service,
        patch("app.services.scheduler.get_messaging_api") as mock_api,
        patch.object(
            DDAScheduler, "_get_or_create_profile", new_callable=AsyncMock
        ) as mock_profile,
        patch.object(DDAScheduler, "_should_send") as mock_should_send,
    ):

        mock_user = MagicMock()
        mock_user.id = "test_user_123"
        mock_user.push_enabled = True
        mock_user.push_times = {"morning": "08:00", "midday": "12:30", "night": "21:00"}

        profile = MagicMock()
        profile.morning_time = "08:00"
        profile.midday_time = "12:30"
        profile.night_time = "21:00"
        profile.last_morning_date = None
        profile.last_midday_date = None
        profile.last_night_date = None
        mock_profile.return_value = profile

        mock_api.return_value = AsyncMock()
        mock_quest_service.trigger_push_quests = AsyncMock()
        mock_quest_service.get_daily_quests = AsyncMock(return_value=[])
        mock_quest_service.get_daily_habits = AsyncMock(return_value=[])

        mock_should_send.side_effect = [True, False, False]

        mock_session = AsyncMock()
        await scheduler._process_user(mock_session, mock_user)

        mock_quest_service.trigger_push_quests.assert_called_once_with(
            mock_session, "test_user_123", time_block="Morning"
        )


@pytest.mark.asyncio
async def test_push_respects_user_preference():
    """Verify users with push_enabled=False are skipped."""
    scheduler = DDAScheduler()

    with (
        patch("app.services.scheduler.AsyncSessionLocal") as mock_session_local,
        patch.object(
            DDAScheduler, "_process_user", new_callable=AsyncMock
        ) as mock_process,
        patch.object(DDAScheduler, "_maybe_refresh_shop", new_callable=AsyncMock),
    ):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        mock_user = MagicMock()
        mock_user.id = "test_user_456"
        mock_user.push_enabled = False

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_user]
        mock_session.execute = AsyncMock(return_value=mock_result)

        await scheduler._push_tick()

        mock_process.assert_not_called()
