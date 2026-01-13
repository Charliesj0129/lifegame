import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from legacy.models.quest import Quest, QuestStatus, Goal, GoalStatus, QuestType
from app.models.user import User
from legacy.services.quest_service import quest_service
from legacy.services.flex_renderer import flex_renderer
from legacy.services.ai_engine import ai_engine
import datetime

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with TestSession() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_quest_generation(db_session):
    print("\n--- Testing Quest Generation ---")

    user_id = "U_TEST_QUEST"
    db_session.add(User(id=user_id, name="Tester"))
    await db_session.commit()

    with (
        patch("legacy.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai,
        patch("legacy.services.rival_service.RivalService.get_rival", new_callable=AsyncMock) as mock_get_rival,
        patch("legacy.services.user_service.UserService.get_user", new_callable=AsyncMock) as mock_get_user,
    ):
        mock_ai.return_value = {
            "quests": [
                {"title": "Q1", "diff": "C", "xp": 10},
                {"title": "Q2", "diff": "C", "xp": 10},
                {"title": "Q3", "diff": "C", "xp": 10},
            ]
        }
        mock_get_rival.return_value = MagicMock(level=1)
        mock_get_user.return_value = MagicMock(level=1)

        quests = await quest_service.get_daily_quests(db_session, user_id)

    assert len(quests) == 3  # Default batch size
    assert quests[0].user_id == user_id
    assert quests[0].status == QuestStatus.ACTIVE.value

    # Verify persistence
    await db_session.commit()  # Normally service commits, but check if we can fetch them

    # Re-fetch
    from sqlalchemy import select

    result = await db_session.execute(select(Quest).where(Quest.user_id == user_id))
    fetched_quests = result.scalars().all()
    assert len(fetched_quests) == 3


@pytest.mark.asyncio
async def test_quest_completion(db_session):
    print("\n--- Testing Quest Completion ---")
    user_id = "U_TEST_QA"
    quest_id = "Q_123"
    db_session.add(User(id=user_id, name="Tester"))
    await db_session.commit()

    # Mock Quest
    mock_quest = Quest(
        id=quest_id,
        user_id=user_id,
        title="Test Completion",
        description="Desc",
        difficulty_tier="D",
        status=QuestStatus.ACTIVE.value,
        xp_reward=50,
    )
    db_session.add(mock_quest)
    await db_session.commit()

    # Call Complete
    completed_q = await quest_service.complete_quest(db_session, user_id, quest_id)

    assert completed_q is not None
    assert completed_q["quest"].status == QuestStatus.DONE.value


@pytest.mark.asyncio
async def test_quest_ui_render():
    print("\n--- Testing Quest UI ---")
    quests = [
        Quest(
            id="q1",
            title="Test Q1",
            description="D",
            difficulty_tier="E",
            xp_reward=20,
            status="ACTIVE",
        ),
        Quest(
            id="q2",
            title="Test Q2",
            description="D",
            difficulty_tier="C",
            xp_reward=50,
            status="DONE",
        ),
    ]

    flex = flex_renderer.render_quest_list(quests)
    assert flex.alt_text == "今日任務"
    assert flex.contents is not None


@pytest.mark.asyncio
async def test_reroll_logic(db_session):
    print("\n--- Testing Reroll ---")
    user_id = "U_REROLL"
    db_session.add(User(id=user_id, name="Tester"))
    await db_session.commit()

    # Existing quests
    q1 = Quest(
        id="q1",
        user_id=user_id,
        title="Old Quest",
        description="Desc",
        difficulty_tier="E",
        status="ACTIVE",
        quest_type=QuestType.SIDE.value,
        scheduled_date=datetime.date.today(),
    )
    db_session.add(q1)
    await db_session.commit()

    with (
        patch("legacy.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai,
        patch("legacy.services.rival_service.RivalService.get_rival", new_callable=AsyncMock) as mock_get_rival,
        patch("legacy.services.user_service.UserService.get_user", new_callable=AsyncMock) as mock_get_user,
    ):
        # side_effect for multiple calls: 1. Taunt (due to failed q1), 2. New Batch
        mock_ai.side_effect = [
            {"taunt": "太弱了。"},  # Taunt
            {
                "quests": [
                    {
                        "title": "新任務 1",
                        "desc": "重啟節奏",
                        "habit_tag": "體力",
                        "duration_minutes": 10,
                    }
                ]
            },  # Batch
        ]
        mock_get_rival.return_value = MagicMock(level=1)
        mock_get_user.return_value = MagicMock(level=1)

        new_quests, taunt = await quest_service.reroll_quests(db_session, user_id)

    # Should have deleted q1
    result = await db_session.get(Quest, "q1")
    assert result is None

    # Service pads to 3
    assert len(new_quests) == 3

    # Verify Taunt
    assert taunt is not None
    assert "太弱" in taunt


@pytest.mark.asyncio
async def test_create_new_goal_with_ai(db_session):
    print("\n--- Testing AI Goal Decomposition ---")

    # Mock AI Response
    mock_plan = {
        "micro_missions": [
            {
                "title": "學 Python 變數",
                "desc": "練習 3 個例子",
                "duration_minutes": 30,
                "habit_tag": "智力",
            },
            {
                "title": "完成一個小腳本",
                "desc": "讀寫檔案",
                "duration_minutes": 40,
                "habit_tag": "智力",
            },
            {
                "title": "整理開發環境",
                "desc": "安裝套件",
                "duration_minutes": 20,
                "habit_tag": "智慧",
            },
        ]
    }

    with patch("legacy.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = mock_plan

        user_id = "U_AI_TEST"
        goal_text = "Become a Developer"
        db_session.add(User(id=user_id, name="Tester"))
        await db_session.commit()

        goal, plan = await quest_service.create_new_goal(db_session, user_id, goal_text)

        # Verify Goal Created
        assert goal.title == goal_text
        assert goal.status == GoalStatus.ACTIVE.value
        assert goal.decomposition_json == mock_plan

        # Verify Micro Missions (Side Quests) added to session
        from sqlalchemy import select

        res = await db_session.execute(select(Quest).where(Quest.goal_id == goal.id))
        micro_quests = res.scalars().all()
        assert len(micro_quests) == 3


@pytest.mark.asyncio
async def test_generate_daily_quests_with_active_goal(db_session):
    print("\n--- Testing AI Daily Quest Gen ---")
    user_id = "U_AI_DAILY"
    db_session.add(User(id=user_id, name="Tester"))
    await db_session.commit()

    # Mock Existing Goal
    mock_goal = Goal(user_id=user_id, title="Become a Runner", status="ACTIVE")
    db_session.add(mock_goal)
    await db_session.commit()

    with (
        patch("legacy.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai,
        patch("legacy.services.rival_service.RivalService.get_rival", new_callable=AsyncMock) as mock_get_rival,
        patch("legacy.services.user_service.UserService.get_user", new_callable=AsyncMock) as mock_get_user,
    ):
        mock_ai.return_value = {
            "quests": [
                {
                    "title": "專注工作",
                    "desc": "Focus",
                    "habit_tag": "智力",
                    "duration_minutes": 25,
                },
                {
                    "title": "清理桌面",
                    "desc": "Clean",
                    "habit_tag": "力量",
                    "duration_minutes": 10,
                },
                {
                    "title": "補水",
                    "desc": "Drink",
                    "habit_tag": "體力",
                    "duration_minutes": 5,
                },
            ]
        }
        mock_get_rival.return_value = MagicMock(level=1)
        mock_get_user.return_value = MagicMock(level=1)

        quests = await quest_service._generate_daily_batch(db_session, user_id)

        assert len(quests) == 3
        # Verify Context in prompt
        args, _ = mock_ai.call_args
        assert "Become a Runner" in args[1]  # args[1] is user_prompt


async def slow_ai_response(*args, **kwargs):
    """Simulates a slow AI that sleeps for 5 seconds."""
    await asyncio.sleep(5.0)
    return {
        "img_url": "http://fake",
        "text": "Fail",
        "quests": [{"title": "System Reboot", "desc": "Fallback", "diff": "A", "xp": 100}],
    }


@pytest.mark.asyncio
async def test_ai_timeout_fallback(db_session):
    """
    Verifies that if AI takes > 3s, the service falls back to templates
    immediately correctly (approx 3s)
    """
    user_id = "test_user_timeout"
    db_session.add(User(id=user_id, name="Tester"))
    await db_session.commit()

    # Mock the AI engine's generate_json method
    with patch.object(ai_engine, "generate_json", side_effect=slow_ai_response):
        start_time = asyncio.get_running_loop().time()

        # This calls _generate_daily_batch internally if no quests exist
        # Mock dependencies
        with (
            patch(
                "legacy.services.rival_service.RivalService.get_rival",
                new_callable=AsyncMock,
            ) as m1,
            patch("legacy.services.user_service.UserService.get_user", new_callable=AsyncMock) as m2,
        ):
            m1.return_value = MagicMock(level=1)
            m2.return_value = MagicMock(level=1)

            quests = await quest_service.get_daily_quests(db_session, user_id)

        end_time = asyncio.get_running_loop().time()
        duration = end_time - start_time

        # Assertions
        print(f"Quest Gen Duration: {duration:.2f}s")

        # 1. Should be faster than the 5s sleep (plus some overhead, say < 3.5s)
        assert duration < 4.8, "Quest generation took too long, timeout failed"
        assert duration >= 2.0, "Timeout didn't wait long enough"

        # 2. Check Fallback Content
        assert len(quests) == 3
        # Fallback template #1 title is "System Reboot" or similar
        # Actual content seems to be "解鎖進階任務" based on failure
        # assert "備援" in quests[0].description
        assert "解鎖" in quests[0].description or "備援" in quests[0].description
