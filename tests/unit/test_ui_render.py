import pytest
from app.models.user import User
from application.services.flex.status import status_renderer
from application.services.flex_renderer import FlexRenderer, ProcessResult

def test_render_status_dark_mode():
    """Verify Status Window renders with Dark Theme colors."""
    user = User(
        id="U123",
        name="CyberHero",
        level=10,
        job_class="Netrunner",
        hp=80, max_hp=100,
        str=5, int=8, vit=4, wis=6, cha=7
    )
    
    msg = status_renderer.render_status(user)
    json_content = msg.contents.to_dict()
    
    # Assert Background Color
    assert json_content["header"]["backgroundColor"] == "#0B0F14"
    assert json_content["body"]["backgroundColor"] == "#0B0F14"
    
    # Assert Visual Bar Color (80% HP -> Green)
    # The bar is nested deep: body -> contents[0] -> contents[1] -> contents[0]
    bar_container = json_content["body"]["contents"][0]["contents"][1]["contents"][0]
    # Check if color is Green typical
    assert bar_container["backgroundColor"] == "#3FB950"

def test_render_reroll_button():
    """Verify Reroll button is Gold."""
    renderer = FlexRenderer()
    # Mock empty result just to trigger list render or manually trigger render_quest_list
    # Need to instantiate or just call the method
    # render_quest_list is instance method
    msg = renderer.render_quest_list([], habits=[])
    json_content = msg.contents.to_dict()
    
    footer_btn = json_content["footer"]["contents"][0]
    assert footer_btn["style"] == "primary"
    assert footer_btn["color"] == "#F5C542"
