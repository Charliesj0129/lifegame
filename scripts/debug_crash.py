import sys
import os
import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def reproduce():
    print("🚀 Starting Reproduction of Create Goal Crash... (Real Env with Patches)")

    # 1. Import real modules
    try:
        from app.core.container import container
        from application.services.quest_service import quest_service
        from application.services.ai_engine import ai_engine
        from app.models.quest import Quest, Goal
    except ImportError as e:
        print(f"❌ ImportError: {e}")
        print("Ensure you are running with 'uv run python3 scripts/debug_crash.py'")
        return

    # 2. Patch AI Engine (Avoid API calls)
    ai_engine.generate_json = AsyncMock(
        return_value={
            "tactical_quests": [{"title": "Test Quest", "desc": "Desc", "diff": "E", "duration_minutes": 10}],
            "daily_habits": [],
            "milestones": [],
        }
    )

    # 3. Patch Adapter
    # We need to simulate the condition: add_node is SYNC and returns LIST
    mock_adapter = MagicMock()
    mock_adapter.add_node.return_value = ["LIST_RETURN"]
    mock_adapter.add_relationship = AsyncMock(return_value=True)

    # Inject into GraphService
    # Ensure graph_service is initialized
    gs = container.graph_service
    gs.adapter = mock_adapter  # Force replace adapter

    # 4. Mock Session (Avoid DB calls)
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result
    # Allow session.add/commit/flush to do nothing (AsyncMock default returns Coroutine, which is awaited safely usually,
    # but session.add is Sync in SQLA 1.4/2.0+ usually, unless async session?
    # AsyncSession.add is Sync. AsyncSession.commit is Async.
    # So we need session.add to be a Mock (Sync), and session.commit to be AsyncMock.
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    try:
        print("Invoking quest_service.create_new_goal...")
        # Logic:
        # ai_engine.generate_json -> AsyncMock (OK)
        # adapter.add_node -> Mock returning List. IF CREAT_NEW_GOAL AWAITS THIS -> ERROR.
        # await adapter.add_relationship -> AsyncMock (OK)

        await quest_service.create_new_goal(session, "u_debug_user", "我想提升睪固酮")
        print("✅ Success! No crash. The await was successfully removed.")

    except TypeError as e:
        if "object list can't be used in 'await' expression" in str(e):
            print("❌ CAUGHT THE BUG! 'add_node' mock (list) was awaited!")
        else:
            print(f"❌ Caught unexpected TypeError: {e}")
            import traceback

            traceback.print_exc()
    except Exception as e:
        print(f"❌ Caught unexpected Exception: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(reproduce())
