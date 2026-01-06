import pytest
from app.services.flex_renderer import flex_renderer
from app.models.user import User
from app.models.quest import Quest
from app.models.lore import LoreProgress
# Wait, let's see what the file actually has first before applying blindly.
# I will cancel this tool call effectively by doing nothing or just reading first.
# Oh I can't cancel. I'll just use the view_file results in next turn.
# I'll output a "dummy" replacement that I think is likely correct IF Quest exists,
# but I suspect Quest is NOT the Pydantic model name or it's not exported.
# I'll wait.


def test_render_status_v2():
    user = User(id="u1", name="Tester", level=5, xp=500, hp=80, max_hp=100, is_hollowed=False)
    lore = [LoreProgress(series="Origins", current_chapter=3)]

    flex = flex_renderer.render_status(user, lore)
    json_data = flex.to_dict()

    # Verify Content
    body_contents = json_data['contents']['body']['contents']

    # Check HP Bar existence
    has_hp = any("生命值" in str(c) and "80 / 100" in str(c) for c in body_contents)
    assert has_hp, "HP Bar missing"

    # Check Hollowed (False)
    has_hollowed = any("瀕死狀態" in str(c) for c in body_contents)
    assert not has_hollowed

    # Check Lore
    has_lore = any("Origins" in str(c) and "第 3 章" in str(c) for c in body_contents) or \
               any("Origins｜第 3 章" in str(c) for c in body_contents)
    assert has_lore, "Lore entry missing"

def test_render_quest_list_v2():
    quests = [Quest(title="Mission 1", difficulty_tier="S", xp_reward=100, status="ACTIVE")]
    class MockHabit:
        def __init__(self, name, streak):
            self.id = "h1"
            self.habit_name = name
            self.zone_streak_days = streak
            self.tier = "T2"

    habits = [MockHabit("Morning Run", 5)]

    flex = flex_renderer.render_quest_list(quests, habits)
    json_data = flex.to_dict()

    body_contents = json_data['contents']['body']['contents']

    # Check Content
    # has_habit = any("Morning Run" in str(c) for c in body_contents)
    has_habit = any("Morning Run" in str(c) for c in body_contents)
    assert has_habit

    # has_quest = any("Mission 1" in str(c) for c in body_contents)
    has_quest = any("Mission 1" in str(c) for c in body_contents)
    assert has_quest

    # Check Sections (Based on file content: "例行模組" and "今日任務")
    has_routines = any("例行模組" in str(c) for c in body_contents)
    assert has_routines, f"Routines Header missing. Found: {[str(c) for c in body_contents if 'text' in str(c)]}"
    
    has_missions = any("今日任務" in str(c) for c in body_contents) 
    assert has_missions, "Missions Header missing"
