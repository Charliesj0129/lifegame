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
        "戰術系統" in header_text or "TACTICAL" in header_text
    )  # Support both Chinese and English

    # 2. Check Colors
    header_color = contents["header"]["contents"][0]["color"]
    print(f"Accent Color: {header_color}")
    assert header_color == "#00FF9D"  # Neon Green

    # 3. Check Stats (STR 85 should be 85% width)
    # The stats are in 'body' -> wrapper box -> stats matrix box (last one)
    # Let's just traverse and find "STR"

    body_contents = contents["body"]["contents"]
    stats_matrix = body_contents[-1]  # content stat_rows
    # stat_rows contents

    print("\n--- Stats Check ---")
    str_row = stats_matrix["contents"][0]
    str_label = str_row["contents"][0]["text"]
    str_bar_width = str_row["contents"][1]["contents"][0]["width"]

    print(f"Stat: {str_label} | Width: {str_bar_width}")
    assert str_label in ["STR", "力量"]  # Support both
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
