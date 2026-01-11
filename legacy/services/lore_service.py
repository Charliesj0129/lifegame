from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from legacy.models.lore import LoreEntry, LoreProgress
import logging

logger = logging.getLogger(__name__)


class LoreService:
    async def get_user_progress(self, session: AsyncSession, user_id: str) -> list[LoreProgress]:
        stmt = select(LoreProgress).where(LoreProgress.user_id == user_id).order_by(LoreProgress.series)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_unlocked_lore(self, session: AsyncSession, user_id: str) -> list[LoreEntry]:
        """
        Returns all LoreEntries that the user has unlocked based on LoreProgress.
        Also returns User-specific generated lore (series="User:{id}").
        """
        # 1. Get Progress
        stmt_prog = select(LoreProgress).where(LoreProgress.user_id == user_id)
        result_prog = await session.execute(stmt_prog)
        progress_map = {p.series: p.current_chapter for p in result_prog.scalars().all()}

        # 2. Fetch all relevant entries
        # Requires complex query or fetching all and filtering?
        # Better to query:
        # (series == 'User:{id}') OR (progress_map.get(series) >= chapter)
        # SQL construct:
        # SELECT * FROM lore_entries WHERE series = 'User:{id}'
        # OR (series IN keys AND chapter <= val) -- hard to express in single SQL unless joined.
        # Let's fetch all relevant series first.

        stmt = select(LoreEntry).order_by(LoreEntry.created_at.desc())
        result = await session.execute(stmt)
        all_entries = result.scalars().all()

        unlocked = []
        user_series = f"User:{user_id}"

        for entry in all_entries:
            if entry.series == user_series:
                unlocked.append(entry)
            elif entry.series in progress_map:
                if entry.chapter <= progress_map[entry.series]:
                    unlocked.append(entry)

        return unlocked

    async def unlock_next_chapter(self, session: AsyncSession, user_id: str, series: str) -> LoreProgress:
        """
        Unlocks the next chapter for a given series.
        Creates progress record if not exists.
        """
        stmt = select(LoreProgress).where(LoreProgress.user_id == user_id, LoreProgress.series == series)
        result = await session.execute(stmt)
        prog = result.scalars().first()

        if not prog:
            prog = LoreProgress(user_id=user_id, series=series, current_chapter=1)
            session.add(prog)
        else:
            prog.current_chapter += 1

        await session.commit()
        return prog

    async def unlock_data_shard(self, session: AsyncSession, user_id: str, series: str = "MainStory") -> LoreEntry:
        stmt = select(LoreProgress).where(LoreProgress.user_id == user_id, LoreProgress.series == series)
        result = await session.execute(stmt)
        prog = result.scalars().first()

        if not prog:
            prog = LoreProgress(user_id=user_id, series=series, current_chapter=0)
            session.add(prog)
            await session.commit()

        next_chapter = (prog.current_chapter or 0) + 1

        entry_stmt = select(LoreEntry).where(
            LoreEntry.series == series,
            LoreEntry.chapter == next_chapter,
        )
        entry = (await session.execute(entry_stmt)).scalars().first()

        if not entry:
            title = f"{series}｜第 {next_chapter} 章"
            body = "檔案片段尚未完整同步，請稍後再次嘗試。"
            try:
                from legacy.services.ai_engine import ai_engine

                payload = await ai_engine.generate_json(
                    system_prompt=(
                        "你是賽博檔案系統。生成一段世界觀劇情，需為繁體中文。輸出 JSON: {'title': 'str', 'body': 'str'}"
                    ),
                    user_prompt=f"系列：{series}，章節：{next_chapter}",
                )
                title = payload.get("title", title)
                body = payload.get("body", body)
            except Exception as exc:
                logger.warning("Lore generation failed: %s", exc)

            entry = LoreEntry(
                series=series,
                chapter=next_chapter,
                title=title,
                body=body,
            )
            session.add(entry)

        prog.current_chapter = next_chapter
        session.add(prog)
        await session.commit()
        return entry


lore_service = LoreService()
