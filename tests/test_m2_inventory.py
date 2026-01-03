import pytest
from app.models.user import User
from app.models.gamification import Item, UserItem, ItemType, UserBuff
from app.models.action_log import ActionLog
from app.services.inventory_service import inventory_service
from app.services.settlement_service import settlement_service
from app.services.accountant import accountant
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_use_item_applies_buff(db_session):
    # Setup
    user = User(id="u_inv", name="Tester")
    db_session.add(user)
    
    item = Item(
        id="POT_INT", 
        name="Brain Potion", 
        type=ItemType.CONSUMABLE,
        effect_meta={"buff": "INT", "multiplier": 2.0, "duration_minutes": 30}
    )
    db_session.add(item)
    
    user_item = UserItem(user_id=user.id, item_id=item.id, quantity=2)
    db_session.add(user_item)
    await db_session.commit()

    # Act
    msg = await inventory_service.use_item(db_session, user.id, "Brain")
    
    # Assert
    assert "Applied 2.0x INT Boost" in msg or "Brain Potion" in msg
    
    # Check Buff
    buffs = await inventory_service.get_active_buffs(db_session, user.id)
    assert len(buffs) == 1
    assert buffs[0].target_attribute == "INT"
    assert buffs[0].multiplier == 2.0
    
    # Check Quantity
    await db_session.refresh(user_item)
    assert user_item.quantity == 1

@pytest.mark.asyncio
async def test_accountant_applies_buff():
    # Mock buff
    class MockBuff:
        target_attribute = "INT"
        multiplier = 2.0
        
    xp = 100
    buffs = [MockBuff()]
    
    # Matching Attribute
    new_xp = accountant.apply_buffs(xp, buffs, "INT")
    assert new_xp == 200
    
    # Non-matching
    new_xp_str = accountant.apply_buffs(xp, buffs, "STR")
    assert new_xp_str == 100

@pytest.mark.asyncio
async def test_settlement_report(db_session):
    user = User(id="u_set", name="Settler")
    db_session.add(user)
    
    # Add logs
    now = datetime.now()
    log1 = ActionLog(user_id="u_set", action_text="Code", attribute_tag="INT", difficulty_tier="E", xp_gained=50, timestamp=now)
    log2 = ActionLog(user_id="u_set", action_text="Read", attribute_tag="INT", difficulty_tier="E", xp_gained=50, timestamp=now)
    db_session.add_all([log1, log2])
    await db_session.commit()
    
    report = await settlement_service.generate_weekly_report(db_session, "u_set")
    
    assert "Weekly Settlement" in report
    assert "Total XP Gained: 100" in report
    assert "Main Focus: INT" in report
