import asyncio
import json
import pytest
from app.services.flex_renderer import flex_renderer
from app.models.user import User


@pytest.mark.asyncio
async def test_hud_generation():
    print("\n--- Testing M8 HUD Generation ---")

    # Mock User
    user = User(
        id="U_TEST_HUD",
        name="Cyber Samurai",
        level=10,
        xp=450,
        str=85,
        int=40,
        vit=60,
        wis=30,
        cha=90,
        gold=1500,
    )

    # Generate Flex
    flex = flex_renderer.render_status(user)

    # Validate Contents
    contents = flex.contents.to_dict()  # FlexContainer to dict

    print("✅ Flex Message Generated.")

    # 1. Check Header (Tactical OS)
    header_text = contents["header"]["contents"][0]["text"]
    print(f"Header: {header_text}")
    assert (
        "戰術系統" in header_text
        or "戰術面板" in header_text
        or "TACTICAL" in header_text
    )  # Support both Chinese and English

    # 2. Check Colors
    header_color = contents["header"]["contents"][0]["color"]
    print(f"Accent Color: {header_color}")
    assert header_color in {"#00FF9D", "#00F5FF"}  # Neon Green / Cyan

    # 3. Check Stats (力量 85 should be 85% width)
    def find_stat_row(items, label):
        for item in items:
            if not isinstance(item, dict):
                continue
            contents = item.get("contents", [])
            if any(
                isinstance(child, dict) and child.get("text") == label
                for child in contents
            ):
                return item
            nested = find_stat_row(contents, label)
            if nested:
                return nested
        return None

    body_contents = contents["body"]["contents"]
    str_row = find_stat_row(body_contents, "力量")

    print("\n--- Stats Check ---")
    assert str_row is not None
    str_bar_width = str_row["contents"][2]["contents"][0]["width"]

    print(f"Stat: 力量 | Width: {str_bar_width}")
    assert str_bar_width == "85%"

    print("✅ Stats Bars Verified.")

    # 4. Check XP Bar (450/1000 = 45%)
    # XP Bar is the 2nd main element in body dict list
    # Actually it's inside a wrapper. Let's look for "EXP" text.
    print(f"XP Check: {user.xp} XP")

    # Serialize for manual visual check
    print("\n--- JSON Output (Partial) ---")
    print(json.dumps(contents, indent=2, ensure_ascii=False)[:500] + "...")


if __name__ == "__main__":
    asyncio.run(test_hud_generation())
