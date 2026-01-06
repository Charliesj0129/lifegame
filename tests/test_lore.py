import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.lore_service import lore_service
from app.models.lore import LoreEntry, LoreProgress


@pytest.mark.asyncio
async def test_unlock_next_chapter():
    mock_session = AsyncMock()
    # Mock return of await session.execute(...)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    prog = await lore_service.unlock_next_chapter(mock_session, "u1", "Origin")

    assert prog.current_chapter == 1
    assert prog.series == "Origin"
    assert mock_session.add.called
    assert mock_session.commit.called

    # Mock existing result
    existing = LoreProgress(user_id="u1", series="Origin", current_chapter=1)
    mock_result_existing = MagicMock()
    mock_result_existing.scalars.return_value.first.return_value = existing
    mock_session.execute.return_value = mock_result_existing

    prog2 = await lore_service.unlock_next_chapter(mock_session, "u1", "Origin")
    assert prog2.current_chapter == 2


@pytest.mark.asyncio
async def test_get_unlocked_lore():
    mock_session = AsyncMock()

    # Mock Progress: Origin Lv.2
    mock_prog = [LoreProgress(series="Origin", current_chapter=2)]

    # Mock Entries:
    # 1. User specific (always unlocked)
    # 2. Origin Ch1 (unlocked)
    # 3. Origin Ch3 (locked)
    # 4. Other Ch1 (locked)
    mock_entries = [
        LoreEntry(series="User:u1", chapter=1, title="My Story"),
        LoreEntry(series="Origin", chapter=1, title="Origin Start"),
        LoreEntry(series="Origin", chapter=3, title="Origin Future"),
        LoreEntry(series="Other", chapter=1, title="Hidden"),
    ]

    # Helper to return different mocks for different calls?
    # execute called twice.
    # 1st call: select(LoreProgress)
    # 2nd call: select(LoreEntry)

    mock_result_prog = MagicMock()
    mock_result_prog.scalars.return_value.all.return_value = mock_prog

    mock_result_entries = MagicMock()
    mock_result_entries.scalars.return_value.all.return_value = mock_entries

    mock_session.execute.side_effect = [mock_result_prog, mock_result_entries]

    unlocked = await lore_service.get_unlocked_lore(mock_session, "u1")

    titles = [e.title for e in unlocked]
    assert "My Story" in titles
    assert "Origin Start" in titles
    assert "Origin Future" not in titles
    assert "Hidden" not in titles
