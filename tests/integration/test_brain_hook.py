import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from application.services.user_service import UserService
from application.services.brain_service import AgentPlan, AgentStatUpdate, FlowState
from app.models.user import User
from app.models.base import Base
from app.models.action_log import ActionLog
from app.models.dda import HabitState
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_hook_loop_frustration(db_session):
    # Mock Brain Service to simulate "Frustration logic" without real AI
    with patch("application.services.brain_service.brain_service.think_with_session") as mock_think:
        # Setup Plan: Brain detects failure -> Easy Mode
        mock_think.return_value = AgentPlan(
            narrative="Don't worry, take it easy.",
            stat_update=AgentStatUpdate(xp_amount=50, stat_type="VIT"),
            flow_state={"tier": "E", "tone": "Encourage", "loot_mult": 1.5},
        )

        svc = UserService()
        user_id = "u_hook_1"

        # Act
        result = await svc.process_action(db_session, user_id, "I failed the run")

        # Assert (Effect on User)
        # 1. Narrative passed through
        assert "take it easy" in result.narrative
        # 2. Difficulty adjusted
        assert result.difficulty_tier == "E"  # From Brain
        # 3. XP Applied
        assert result.xp_gained >= 50  # Base 50 + Buffs?

        # Verify Brain was called
        mock_think.assert_called_once()
        args = mock_think.call_args
        assert args[0][1] == user_id  # User ID
        assert "failed" in args[0][2]  # Text
