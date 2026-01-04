import sys
import os
import asyncio
from pathlib import Path

# Add project root
sys.path.append(os.getcwd())

from app.services.rich_menu_service import RichMenuService, RICH_MENU_DATA_PATH
from linebot.v3.messaging import RichMenuArea, RichMenuBounds, MessageAction, URIAction, PostbackAction

# Artifacts Dir (Hardcoded for this session based on context)
ARTIFACTS_DIR = Path("/home/charlie/.gemini/antigravity/brain/2bb82007-c5c5-4cec-bda4-2a62578e8829")

def get_morning_areas():
    # 3 Buttons: Ritual (Top Left), Hydrate (Top Right), Objectives (Bottom)
    return [
        RichMenuArea(
            bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
            action=MessageAction(label="Morning Ritual", text="Start Morning Routine")
        ),
        RichMenuArea(
            bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
            action=MessageAction(label="Hydrate", text="Log: Drank Water")
        ),
        RichMenuArea(
            bounds=RichMenuBounds(x=0, y=843, width=2500, height=843),
            action=MessageAction(label="View Objectives", text="Quests")
        )
    ]

def get_work_areas():
    # 3 Buttons: Focus (Top Left), Insight (Top Right), Break (Bottom)
    return [
        RichMenuArea(
            bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
            action=MessageAction(label="Focus Timer", text="Start Focus")
        ),
        RichMenuArea(
            bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
            action=MessageAction(label="Log Insight", text="Log: Had an idea")
        ),
        RichMenuArea(
            bounds=RichMenuBounds(x=0, y=843, width=2500, height=843),
            action=MessageAction(label="Break", text="Take a Break")
        )
    ]

def get_night_areas():
    # 3 Buttons: Review (Top Left), Journal (Top Right), Meditate (Bottom)
    return [
        RichMenuArea(
            bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
            action=MessageAction(label="Daily Review", text="Daily Review")
        ),
        RichMenuArea(
            bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
            action=MessageAction(label="Journal", text="Log: Journal Entry")
        ),
        RichMenuArea(
            bounds=RichMenuBounds(x=0, y=843, width=2500, height=843),
            action=MessageAction(label="Meditate", text="Log: Meditation")
        )
    ]

def main():
    service = RichMenuService()
    mappings = service._load_mappings()
    
    # 1. Find Images
    # We need to find the files in the artifact dir matching our patterns
    # Since filenames have timestamps, we look for globs
    
    import glob
    try:
        morning_img = glob.glob(str(ARTIFACTS_DIR / "rich_menu_bg_morning_*.jpg"))[0]
        work_img = glob.glob(str(ARTIFACTS_DIR / "rich_menu_bg_work_*.jpg"))[0]
        night_img = glob.glob(str(ARTIFACTS_DIR / "rich_menu_bg_night_*.jpg"))[0]
    except IndexError:
        print("❌ Could not find one of the background images in artifacts.")
        return

    print(f"Found Images:\nMonitor: {morning_img}\nWork: {work_img}\nNight: {night_img}")

    # 2. Create Menus
    new_mappings = mappings.copy()

    # Morning
    print("Creating Morning Menu...")
    mid = service.create_menu("MORNING", get_morning_areas(), morning_img)
    if mid: new_mappings["MORNING"] = mid

    # Work
    print("Creating Work Menu...")
    mid = service.create_menu("WORK", get_work_areas(), work_img)
    if mid: new_mappings["WORK"] = mid

    # Night
    print("Creating Night Menu...")
    mid = service.create_menu("NIGHT", get_night_areas(), night_img)
    if mid: new_mappings["NIGHT"] = mid
    
    # 3. Save
    service._save_mappings(new_mappings)
    
    # 4. Set Default (Morning as default)
    if "MORNING" in new_mappings:
        try:
            service.api.set_default_rich_menu(new_mappings["MORNING"])
            print(f"✅ Set Default Rich Menu to: {new_mappings['MORNING']}")
        except Exception as e:
            print(f"❌ Failed to set default menu: {e}")

    print("✅ Rich Menus Deployed and Saved.")

if __name__ == "__main__":
    main()
