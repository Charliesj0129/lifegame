import datetime
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dda import CompletionLog, DailyOutcome, HabitState

logger = logging.getLogger(__name__)


class DDAService:
    GREEN_MIN = 0.85
    RED_MAX = 0.60
    EMA_ALPHA = 0.25
    TIERS = ["T0", "T1", "T2", "T3"]

    def _zone(self, p: float) -> str:
        if p >= self.GREEN_MIN:
            return "GREEN"
        if p < self.RED_MAX:
            return "RED"
        return "YELLOW"

    def _shift_tier(self, current: str, delta: int) -> str:
        if current not in self.TIERS:
            current = "T1"
        idx = self.TIERS.index(current)
        idx = max(0, min(len(self.TIERS) - 1, idx + delta))
        return self.TIERS[idx]

    async def get_or_create_habit_state(self, session: AsyncSession, user_id: str, habit_tag: str) -> HabitState:
        stmt = select(HabitState).where(
            HabitState.user_id == user_id,
            HabitState.habit_tag == habit_tag,
        )
        state = (await session.execute(stmt)).scalars().first()
        if state:
            return state

        state = HabitState(
            user_id=user_id,
            habit_tag=habit_tag,
            habit_name=habit_tag,
            tier="T1",
            ema_p=0.6,
            last_zone="YELLOW",
            zone_streak_days=0,
            last_outcome_date=None,
        )
        session.add(state)
        await session.commit()
        return state

    async def apply_missed_days(self, session: AsyncSession, user_id: str, habit_tag: str) -> HabitState | None:
        state = await self.get_or_create_habit_state(session, user_id, habit_tag)
        if not state.last_outcome_date:
            return state

        today = datetime.date.today()
        missed_days = max(0, (today - state.last_outcome_date).days - 1)
        if missed_days > 0:
            state.tier = self._shift_tier(state.tier or "T1", -1)
            state.last_zone = "RED"
            state.zone_streak_days = max(1, state.zone_streak_days)
            await session.commit()
        return state

    async def record_completion(
        self,
        session: AsyncSession,
        user_id: str,
        habit_tag: str,
        tier_used: str,
        source: str,
        duration_minutes: int | None = None,
        quest_id: str | None = None,
    ) -> HabitState:
        today = datetime.date.today()
        state = await self.get_or_create_habit_state(session, user_id, habit_tag)

        outcome_stmt = select(DailyOutcome).where(
            DailyOutcome.user_id == user_id,
            DailyOutcome.habit_tag == habit_tag,
            DailyOutcome.date == today,
            DailyOutcome.is_global.is_(False),
        )
        outcome = (await session.execute(outcome_stmt)).scalars().first()
        if outcome:
            outcome.done = True
        else:
            outcome = DailyOutcome(
                user_id=user_id,
                habit_tag=habit_tag,
                date=today,
                done=True,
                is_global=False,
            )
            session.add(outcome)

        global_stmt = select(DailyOutcome).where(
            DailyOutcome.user_id == user_id,
            DailyOutcome.date == today,
            DailyOutcome.is_global.is_(True),
        )
        global_outcome = (await session.execute(global_stmt)).scalars().first()
        if global_outcome:
            global_outcome.done = True
        else:
            global_outcome = DailyOutcome(
                user_id=user_id,
                habit_tag=None,
                date=today,
                done=True,
                is_global=True,
            )
            session.add(global_outcome)

        completion_log = CompletionLog(
            user_id=user_id,
            quest_id=quest_id,
            habit_tag=habit_tag,
            tier_used=tier_used,
            source=source,
            duration_minutes=duration_minutes,
        )
        session.add(completion_log)

        # EMA update
        ema = state.ema_p or 0.0
        new_ema = self.EMA_ALPHA * 1.0 + (1 - self.EMA_ALPHA) * ema
        zone = self._zone(new_ema)
        if zone == state.last_zone:
            state.zone_streak_days = (state.zone_streak_days or 0) + 1
        else:
            state.zone_streak_days = 1
        state.ema_p = new_ema
        state.last_zone = zone
        state.last_outcome_date = today

        if state.zone_streak_days >= 2:
            if zone == "GREEN":
                state.tier = self._shift_tier(state.tier or "T1", 1)
            elif zone == "RED":
                state.tier = self._shift_tier(state.tier or "T1", -1)

        await session.commit()
        return state


dda_service = DDAService()
