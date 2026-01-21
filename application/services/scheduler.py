"""
DDA Scheduler Service

Implements scheduled push notifications for the DDA system using APScheduler.
Supports per-user timezone and custom push times.
"""

import asyncio
import logging
import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.dda import PushProfile, DailyOutcome
from application.services.quest_service import quest_service, QuestService
from application.services.rival_service import rival_service
from application.services.flex_renderer import flex_renderer
from application.services.line_bot import get_messaging_api
from linebot.v3.messaging import (
    PushMessageRequest,
    QuickReply,
    QuickReplyItem,
    PostbackAction,
)

logger = logging.getLogger(__name__)


class DDAScheduler:
    """
    Manages scheduled DDA push notifications.

    Time blocks:
    - Morning: 08:00 - Generate and push daily quests
    - Midday: 12:30 - Reminder for incomplete quests
    - Night: 21:00 - Daily review and rival advancement
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False
        self._lock = asyncio.Lock()
        self._last_shop_refresh_date: datetime.date | None = None

    def start(self):
        """Start the scheduler with all configured jobs."""
        if self._is_running:
            logger.warning("Scheduler already running")
            return

        interval = max(30, settings.SCHEDULER_INTERVAL_SECONDS)
        self.scheduler.add_job(
            self._push_tick,
            IntervalTrigger(seconds=interval),
            id="push_tick",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # Executive System Tick (Hourly)
        self.scheduler.add_job(
            self._executive_tick,
            IntervalTrigger(minutes=60),
            id="executive_tick",
            replace_existing=True,
            misfire_grace_time=300,
        )

        self.scheduler.start()
        self._is_running = True
        logger.info("DDA Scheduler started with interval job (%ss)", interval)

    def shutdown(self):
        """Gracefully shutdown the scheduler."""
        if self._is_running:
            self.scheduler.shutdown(wait=True)
            self._is_running = False
            logger.info("DDA Scheduler shutdown complete")

    async def _get_all_users(self, session: AsyncSession) -> list[User]:
        """Fetch all users for push preference checks."""
        stmt = select(User)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def _push_tick(self):
        """
        Single scheduler tick that checks per-user local time and sends pushes.
        Uses batched execution to prevent head-of-line blocking.
        """
        if self._lock.locked():
            return

        BATCH_SIZE = 10  # Process 10 users concurrently

        async with self._lock:
            async with AsyncSessionLocal() as session:
                users = await self._get_all_users(session)
                await self._maybe_refresh_shop(session, users)

                # Split into chunks for basic rate limiting/batching
                for i in range(0, len(users), BATCH_SIZE):
                    chunk = users[i : i + BATCH_SIZE]
                    tasks = []
                    for user in chunk:
                        if not user.push_enabled:
                            continue
                        tasks.append(self._process_user_safe(session, user))

                    if tasks:
                        await asyncio.gather(*tasks)

    async def _process_user_safe(self, session: AsyncSession, user: User):
        """Wrapper to catch exceptions per user task."""
        try:
            await self._process_user(session, user)
        except Exception as e:
            logger.error("Push tick failed for %s: %s", user.id, e)

    async def _executive_tick(self):
        """
        Runs the Executive System Logic for all users.
        """
        if self._lock.locked():
            return

        from application.services.brain_service import brain_service

        async with self._lock:
            async with AsyncSessionLocal() as session:
                users = await self._get_all_users(session)
                for user in users:
                    try:
                        action = await brain_service.execute_system_judgment(session, str(user.id))
                        if action:
                            logger.info(f"EXECUTIVE ACTION for {user.id}: {action.action_type} - {action.reason}")
                    except Exception as e:
                        logger.error(f"Executive tick failed for {user.id}: {e}")

    async def _get_or_create_profile(self, session: AsyncSession, user_id: str) -> PushProfile:
        result = await session.execute(select(PushProfile).where(PushProfile.user_id == user_id))
        profile = result.scalars().first()
        if profile:
            return profile
        profile = PushProfile(user_id=user_id)
        session.add(profile)
        await session.commit()
        return profile

    def _safe_timezone(self, tz_name: str | None) -> ZoneInfo:
        try:
            return ZoneInfo(tz_name or "Asia/Taipei")
        except Exception:
            return ZoneInfo("UTC")

    def _should_send(
        self,
        now_local: datetime.datetime,
        target_time: str,
        last_sent: datetime.date | None,
    ) -> bool:
        if not target_time:
            return False
        if now_local.strftime("%H:%M") != target_time:
            return False
        return last_sent != now_local.date()

    def _build_quick_reply(self) -> QuickReply:
        return QuickReply(
            items=[
                QuickReplyItem(
                    action=PostbackAction(
                        label="🔄 重新生成",
                        data="action=reroll_quests",
                        display_text="重新生成任務...",
                    )
                ),
                QuickReplyItem(
                    action=PostbackAction(
                        label="✅ 全部接受",
                        data="action=accept_all_quests",
                        display_text="全部接受任務...",
                    )
                ),
            ]
        )

    async def _maybe_refresh_shop(self, session: AsyncSession, users: list[User]) -> None:
        now = datetime.datetime.utcnow().date()
        if self._last_shop_refresh_date == now:
            return
        from application.services.shop_service import shop_service

        await shop_service.refresh_daily_stock(session)
        api = get_messaging_api()
        if api:
            from linebot.v3.messaging import TextMessage

            for user in users:
                if not user.push_enabled:
                    continue
                try:
                    await api.push_message(
                        PushMessageRequest(
                            to=user.id,
                            messages=[TextMessage(text="🛒 黑市已更新，稀有貨物已上架。")],
                        )
                    )
                except Exception as exc:
                    logger.warning("Shop refresh push failed for %s: %s", user.id, exc)
        self._last_shop_refresh_date = now

    async def _process_user(self, session: AsyncSession, user: User) -> None:
        tz = self._safe_timezone(user.push_timezone)
        now_local = datetime.datetime.now(tz)

        profile = await self._get_or_create_profile(session, user.id)
        times = user.push_times or {}
        morning_time = times.get("morning") or profile.morning_time or "08:00"
        midday_time = times.get("midday") or profile.midday_time or "12:30"
        night_time = times.get("night") or profile.night_time or "21:00"

        api = get_messaging_api()
        if not api:
            return

        if self._should_send(now_local, morning_time, profile.last_morning_date):
            # Explicit cast for mypy if needed, or rely on import
            # qs: QuestService = quest_service
            if user.id:
                await quest_service.trigger_push_quests(session, str(user.id), time_block="Morning")
                quests = await quest_service.get_daily_quests(session, str(user.id))
                habits = await quest_service.get_daily_habits(session, str(user.id))
                dda_hint = await self._daily_hint(session, str(user.id))
            flex = flex_renderer.render_push_briefing("🌅 早安任務", quests, habits, dda_hint)
            flex.quick_reply = self._build_quick_reply()

            # Build messages list
            messages_to_push = [flex]

            # Generate Voice Briefing (Optional)
            try:
                from application.services.audio_service import audio_service

                quest_count = len(quests)
                habit_count = len(habits) if habits else 0
                summary_text = f"早安，今日有 {quest_count} 個任務和 {habit_count} 個習慣。請開始行動。"
                audio_msg = await audio_service.generate_briefing_audio(summary_text)
                if audio_msg:
                    messages_to_push.append(audio_msg)
            except Exception as e:
                logger.warning(f"Audio briefing skipped: {e}")

            await api.push_message(PushMessageRequest(to=user.id, messages=messages_to_push))
            profile.last_morning_date = now_local.date()
            await session.commit()
            return

        if self._should_send(now_local, midday_time, profile.last_midday_date):
            # qs: QuestService = quest_service
            await quest_service.trigger_push_quests(session, str(user.id), time_block="Midday")
            quests = await quest_service.get_daily_quests(session, str(user.id))
            habits = await quest_service.get_daily_habits(session, str(user.id))
            incomplete = [q for q in quests if q.status != "DONE"]
            reminder = None
            if incomplete:
                reminder = "中午提醒：尚有未完成任務，先完成最小一步。"
            else:
                reminder = "中午提醒：今日任務已完成，保持節奏。"
            flex = flex_renderer.render_push_briefing("🧠 中午提醒", incomplete or quests, habits, reminder)
            await api.push_message(PushMessageRequest(to=user.id, messages=[flex]))
            profile.last_midday_date = now_local.date()
            await session.commit()
            return

        if self._should_send(now_local, night_time, profile.last_night_date):
            from application.services.hp_service import hp_service

            await hp_service.calculate_daily_drain(session, user)
            quests = await quest_service.get_daily_quests(session, user.id)
            completed = [q for q in quests if q.status == "DONE"]
            if quests and len(completed) == len(quests):
                hint = "🎉 今日任務全數完成！"
            else:
                hint = "🌙 尚有任務未完成，請挑選最小步驟完成。"

            all_done = bool(quests) and len(completed) == len(quests)
            await self._update_daily_outcome(session, user.id, all_done, bool(quests))
            await rival_service.advance_daily_briefing(session, user)
            flex = flex_renderer.render_push_briefing("🌙 夜間結算", quests, [], hint)
            await api.push_message(PushMessageRequest(to=user.id, messages=[flex]))
            profile.last_night_date = now_local.date()
            await session.commit()

    async def trigger_manual_push(self, user_id: str, time_block: str = "Morning"):
        """
        Manually trigger a push for testing purposes.
        """
        async with AsyncSessionLocal() as session:
            qs: QuestService = quest_service
            await qs.trigger_push_quests(session, user_id, time_block)  # type: ignore[attr-defined]
            logger.info(f"Manual push triggered for user {user_id}, block={time_block}")

    async def _daily_hint(self, session: AsyncSession, user_id: str) -> str | None:
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        stmt = select(DailyOutcome).where(
            DailyOutcome.user_id == user_id,
            DailyOutcome.is_global.is_(True),
            DailyOutcome.date == yesterday,
        )
        result = await session.execute(stmt)
        outcome = result.scalars().first()
        if outcome and not outcome.done:
            return "偵測到能量低落：今日任務已降階，先穩住連勝。"
        return None

    async def _update_daily_outcome(self, session: AsyncSession, user_id: str, done: bool, has_quests: bool) -> None:
        today = datetime.date.today()
        stmt = select(DailyOutcome).where(
            DailyOutcome.user_id == user_id,
            DailyOutcome.date == today,
            DailyOutcome.is_global.is_(True),
        )
        outcome = (await session.execute(stmt)).scalars().first()
        if outcome:
            outcome.done = done
        else:
            outcome = DailyOutcome(
                user_id=user_id,
                habit_tag=None,
                date=today,
                done=done,
                is_global=True,
            )
            session.add(outcome)

        user = await session.get(User, user_id)
        if user:
            user.penalty_pending = bool(has_quests and not done)
            session.add(user)
        await session.commit()


# Singleton instance
dda_scheduler = DDAScheduler()
