from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.lore import LoreEntry, LoreProgress
from application.services.ai_engine import ai_engine
import logging

logger = logging.getLogger(__name__)


class LoreService:
    # Thresholds: Chapter X unlocks at Level Y
    LEVEL_THRESHOLDS = {1: 1, 2: 5, 3: 10, 4: 20, 5: 30, 6: 50}

    async def check_lore_unlock(self, session: AsyncSession, user_id: str, user_level: int) -> LoreEntry | None:
        """
        Checks if a new chapter should be unlocked based on user level.
        Generates and saves the chapter if unlocked.
        """
        # 1. Get Progress
        stmt = select(LoreProgress).where(LoreProgress.user_id == user_id, LoreProgress.series == "main")
        progress = (await session.execute(stmt)).scalars().first()

        if not progress:
            progress = LoreProgress(user_id=user_id, series="main", current_chapter=0)
            session.add(progress)
            await session.commit()  # Ensure ID exists

        next_chapter = progress.current_chapter + 1
        required_level = self.LEVEL_THRESHOLDS.get(next_chapter)

        if not required_level:
            return None  # End of content

        if user_level >= required_level:
            # Unlock!
            logger.info(f"Unlocking Lore Chapter {next_chapter} for {user_id}")
            chapter_entry = await self._generate_chapter(session, user_id, next_chapter)

            if chapter_entry:
                progress.current_chapter = next_chapter
                session.add(progress)
                await session.commit()
                return chapter_entry

        return None

    async def unlock_next_chapter(self, session: AsyncSession, user_id: str, user_level: int) -> LoreEntry | None:
        """Alias for check_lore_unlock"""
        return await self.check_lore_unlock(session, user_id, user_level)

    async def _generate_chapter(self, session: AsyncSession, user_id: str, chapter: int) -> LoreEntry:
        """Generates chapter content via AI."""
        # Check if already exists (global lore? or per user? LoreEntry model seems generic)
        # Assuming Lore is unique per user for now (Personalized Story)

        system_prompt = (
            "Role: Cyberpunk RPG Novelist. "
            "Task: Write a short story chapter (approx 150 words). "
            f"Series: LifeOS - The Awakening. Chapter: {chapter}. "
            "Setting: A dystopian future where self-discipline determines social standing. "
            "Language: ALWAYS use Traditional Chinese (繁體中文). "
            "Output JSON: {'title': 'str', 'body': 'str'}"
        )

        context_prompt = (
            f"Chapter {chapter}. The protagonist (User) has reached Level {self.LEVEL_THRESHOLDS.get(chapter)}."
        )

        try:
            data = await ai_engine.generate_json(system_prompt, context_prompt)
            title = data.get("title", f"Chapter {chapter}")
            body = data.get("body", "Content missing...")

            entry = LoreEntry(
                series=f"User:{user_id}",  # Unique series per user
                chapter=chapter,
                title=title,
                body=body,
            )
            session.add(entry)
            # Commit happens in caller for atomicity with progress,
            # BUT we need entry.id if we return it?
            # Caller commits both progress and entry.
            return entry

        except Exception as e:
            logger.error(f"Lore Gen Failed: {e}")
            return None

    async def get_user_lore(self, session: AsyncSession, user_id: str) -> list[LoreEntry]:
        """Returns all unlocked lore for user."""
        stmt = select(LoreEntry).where(LoreEntry.series == f"User:{user_id}").order_by(LoreEntry.chapter)
        return (await session.execute(stmt)).scalars().all()

    async def get_user_progress(self, session: AsyncSession, user_id: str) -> list[LoreProgress]:
        """Returns user's lore progress records (for Status card display)."""
        stmt = select(LoreProgress).where(LoreProgress.user_id == user_id).order_by(LoreProgress.series)
        result = await session.execute(stmt)
        return result.scalars().all()


lore_service = LoreService()
