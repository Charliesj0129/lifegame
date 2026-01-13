import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from legacy.services.loot_service import LootService
from legacy.services.user_service import UserService
from legacy.models.gamification import ItemRarity
from app.models.user import User
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_loot_drop_weights():
    """Verify that LootService uses the new 'Dark Pattern' weights."""
    loot_svc = LootService()

    # Check weights directly
    assert loot_svc.rarity_weights[ItemRarity.COMMON] == 50.0
    assert loot_svc.rarity_weights[ItemRarity.LEGENDARY] == 1.0

    # Statistical Test (Monte Carlo)
    # We mock _select_rarity to avoid randomness if we wanted deterministic,
    # but here we want to verify the probability roughly works if we trust random.choices.
    # Instead, let's just verify the structure.

    with patch("random.choices") as mock_choices:
        mock_choices.return_value = [ItemRarity.LEGENDARY]
        rarity = loot_svc._select_rarity()
        assert rarity == ItemRarity.LEGENDARY

        # Verify call args
        args, kwargs = mock_choices.call_args
        weights = kwargs.get("weights")
        assert weights[4] == 1.0  # Legendary at index 4


@pytest.mark.asyncio
async def test_penalty_soft_death():
    """Verify 'The Abyss' level reset mechanism."""
    svc = UserService()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    user = User(id="test_sub", level=50, xp=9999)

    await svc.apply_penalty(mock_session, user, penalty_type="SOFT_DEATH")

    assert user.level == 1
    assert user.xp == 0
    mock_session.add.assert_called_with(user)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_hollowing_true():
    """Verify Hollowing triggers after 48h inactivity."""
    svc = UserService()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    now = datetime.now(timezone.utc)
    past = now - timedelta(hours=49)  # 49 hours ago

    user = User(id="test_hollow", last_active_date=past, is_hollowed=False)

    is_hollowed = await svc.check_hollowing(mock_session, user)

    assert is_hollowed is True
    assert user.is_hollowed is True
    assert user.hp_status == "HOLLOWED"
    mock_session.add.assert_called_with(user)


@pytest.mark.asyncio
async def test_check_hollowing_false():
    """Verify Hollowing does NOT trigger if active recently."""
    svc = UserService()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    now = datetime.now(timezone.utc)
    recent = now - timedelta(hours=10)  # 10 hours ago

    user = User(id="test_safe", last_active_date=recent, is_hollowed=False)

    is_hollowed = await svc.check_hollowing(mock_session, user)

    assert is_hollowed is False
    assert user.is_hollowed is False
    mock_session.add.assert_not_called()
