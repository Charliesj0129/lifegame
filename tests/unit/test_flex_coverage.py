import pytest
from application.services.flex_renderer import FlexRenderer
from app.models.user import User
from app.models.quest import Quest, QuestStatus


@pytest.mark.asyncio
async def test_flex_renderer_coverage():
    renderer = FlexRenderer()

    # 1. Render Status
    user = User(id="u1", name="Tester", level=5, hp=80, max_hp=100, gold=500, xp=120)
    msg = renderer.render_status(user)
    assert msg.type == "flex"

    # 2. Render Quest List
    q1 = Quest(title="Q1", difficulty_tier="E", status="ACTIVE")
    q2 = Quest(title="Q2", difficulty_tier="S", status="DONE")
    msg_q = renderer.render_quest_list([q1, q2])
    assert msg_q.type == "flex"

    # 3. Render Inventory
    class MockItem:
        def __init__(self, name, price=0):
            self.id = "i_mock"
            self.name = name
            self.rarity = "COMMON"
            self.type = "CONSUMABLE"
            self.description = "Desc"
            self.price = price

    msg_inv = renderer.render_inventory(user, [(MockItem("Item"), 1)])
    assert msg_inv.type == "flex"

    # 4. Render Shop List
    msg_shop = renderer.render_shop_list([MockItem("Potion", 10)], 500)
    assert msg_shop.type == "flex"

    # 5. Render Help
    msg_help = renderer.render_help_card({})
    assert msg_help.type == "flex"

    # 6. Render Dashboard (mapped to render_status or render_profile?)
    # render_profile(self, user)
    msg_prof = renderer.render_profile(user)
    assert msg_prof.type == "flex"
