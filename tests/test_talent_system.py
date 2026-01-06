"""
天賦系統單元測試
Tests for Talent Build System (Phase 7)
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user import User
from app.models.talent import TalentTree, ClassType, EffectType, INITIAL_TALENTS
from app.services.talent_service import talent_service


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Seed talents
        for talent_data in INITIAL_TALENTS:
            talent = TalentTree(**talent_data)
            session.add(talent)
        await session.commit()
        
        # Create test user
        user = User(id="test_user", name="Test", talent_points=5, streak_count=3)
        session.add(user)
        await session.commit()
        
        yield session


@pytest.mark.asyncio
async def test_talent_seed_data():
    """Verify seed talent data structure."""
    assert len(INITIAL_TALENTS) == 9
    
    class_counts = {ClassType.WARLORD: 0, ClassType.ALCHEMIST: 0, ClassType.SHADOW: 0}
    for t in INITIAL_TALENTS:
        class_counts[t["class_type"]] += 1
    
    assert class_counts[ClassType.WARLORD] == 3
    assert class_counts[ClassType.ALCHEMIST] == 3
    assert class_counts[ClassType.SHADOW] == 3


@pytest.mark.asyncio
async def test_get_talent_tree(db_session):
    """Test fetching talent tree for a user."""
    tree = await talent_service.get_talent_tree(db_session, "test_user")
    
    assert len(tree) == 9
    
    # All should be unlocked for tier 1, locked for tier 2+
    tier1_talents = [t for t in tree if t["tier"] == 1]
    tier2_talents = [t for t in tree if t["tier"] == 2]
    
    assert all(t["unlocked"] for t in tier1_talents)
    assert all(not t["unlocked"] for t in tier2_talents)


@pytest.mark.asyncio
async def test_learn_talent_success(db_session):
    """Test learning a tier 1 talent."""
    success, msg = await talent_service.learn_talent(db_session, "test_user", "STR_01_BLOODLUST")
    
    assert success
    assert "嗜血" in msg
    
    # Check user talent points decreased
    from sqlalchemy import select
    user = (await db_session.execute(select(User).where(User.id == "test_user"))).scalar_one()
    assert user.talent_points == 4  # Started with 5, spent 1


@pytest.mark.asyncio
async def test_learn_talent_requires_parent(db_session):
    """Test that tier 2 talents require parent talent."""
    # Try to learn tier 2 without tier 1
    success, msg = await talent_service.learn_talent(db_session, "test_user", "STR_02_IRON_WILL")
    
    assert not success
    assert "前置" in msg


@pytest.mark.asyncio
async def test_learn_talent_with_parent(db_session):
    """Test learning tier 2 after tier 1."""
    # Learn tier 1 first
    await talent_service.learn_talent(db_session, "test_user", "STR_01_BLOODLUST")
    
    # Now learn tier 2
    success, msg = await talent_service.learn_talent(db_session, "test_user", "STR_02_IRON_WILL")
    
    assert success
    assert "鋼鐵意志" in msg


@pytest.mark.asyncio
async def test_calculate_bonus_xp_gain_streak(db_session):
    """Test XP bonus calculation with Bloodlust talent (streak-based)."""
    # Learn Bloodlust (tier 1)
    await talent_service.learn_talent(db_session, "test_user", "STR_01_BLOODLUST")
    
    # Calculate bonus with 3-day streak
    bonus = await talent_service.calculate_bonus(
        db_session, "test_user", EffectType.XP_GAIN, streak=3
    )
    
    # Bloodlust: +5% per streak day, 3 days = +15%
    assert abs(bonus - 1.15) < 0.01


@pytest.mark.asyncio
async def test_calculate_bonus_no_talents(db_session):
    """Test bonus calculation with no talents returns 1.0."""
    bonus = await talent_service.calculate_bonus(
        db_session, "test_user", EffectType.XP_GAIN, streak=5
    )
    
    assert bonus == 1.0


@pytest.mark.asyncio
async def test_get_player_class_empty(db_session):
    """Test player class when no talents learned."""
    class_type, class_name, emoji = await talent_service.get_player_class(db_session, "test_user")
    
    assert class_name == "無流派"
    assert emoji == "⚪"


@pytest.mark.asyncio
async def test_get_player_class_warlord(db_session):
    """Test player class detection as Warlord."""
    await talent_service.learn_talent(db_session, "test_user", "STR_01_BLOODLUST")
    
    class_type, class_name, emoji = await talent_service.get_player_class(db_session, "test_user")
    
    assert class_type == ClassType.WARLORD
    assert class_name == "狂戰士"
    assert emoji == "🔴"


@pytest.mark.asyncio
async def test_get_player_class_for_ai(db_session):
    """Test AI personality info based on player class."""
    await talent_service.learn_talent(db_session, "test_user", "LCK_01_EVASION")
    
    ai_info = await talent_service.get_player_class_for_ai(db_session, "test_user")
    
    assert ai_info["class_type"] == ClassType.SHADOW
    assert "影行者" in ai_info["class_name"]
    assert ai_info["ai_tone"] == "mysterious"
    assert "閃避" in ai_info["keywords"]


@pytest.mark.asyncio
async def test_check_penalty_evasion_no_talent(db_session):
    """Test evasion check with no Shadow talent."""
    evaded, msg = await talent_service.check_penalty_evasion(db_session, "test_user")
    
    # Should never evade without the talent
    assert not evaded
    assert msg == ""


@pytest.mark.asyncio
async def test_check_penalty_evasion_with_talent(db_session):
    """Test evasion check with Shadow Evasion talent."""
    await talent_service.learn_talent(db_session, "test_user", "LCK_01_EVASION")
    
    # Run multiple times to statistically confirm evasion works
    evade_count = 0
    for _ in range(100):
        evaded, msg = await talent_service.check_penalty_evasion(db_session, "test_user")
        if evaded:
            evade_count += 1
            assert "閃避" in msg
    
    # 20% evasion chance, expect ~15-25 evades in 100 trials
    assert 5 < evade_count < 40  # Wide range due to randomness
