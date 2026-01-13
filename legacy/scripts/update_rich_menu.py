import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from legacy.services.rich_menu_service import rich_menu_service
from app.core.config import settings


async def main():
    print("🚀 Updating Rich Menu to v2 Control Panel...")

    if not settings.LINE_CHANNEL_ACCESS_TOKEN:
        print("❌ Error: LINE_CHANNEL_ACCESS_TOKEN not set.")
        return

    # 1. Cleanup Old Menu
    old_id = rich_menu_service.get_menu_id_by_name("LIFGAME_MAIN")
    if old_id:
        print(f"🗑️ Deleting old menu: {old_id}")
        try:
            rich_menu_service.api.delete_rich_menu(old_id)
        except Exception as e:
            print(f"⚠️ Failed to delete old menu: {e}")

    # 2. Create New Menu
    print("✨ Creating new menu...")
    mappings = rich_menu_service.setup_menus()
    new_id = mappings.get("MAIN")

    if new_id:
        print(f"✅ Created new menu: {new_id}")

        # 3. Set Default
        print("🔗 Setting as Default for all users...")
        try:
            rich_menu_service.blob_api.api_client.call_api(
                "/v2/bot/user/all/richmenu/{richMenuId}",
                "POST",
                path_params={"richMenuId": new_id},
                header_params={"Authorization": f"Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}"},
            )
            print("✅ Default menu set successfully!")
        except Exception:
            # Fallback if the raw call fails, try standard SDK method if available or just print error
            try:
                rich_menu_service.api.set_default_rich_menu(new_id)
                print("✅ Default menu set successfully (standard SDK)!")
            except Exception as e2:
                print(f"❌ Failed to set default menu: {e2}")

    else:
        print("❌ Failed to create menu.")


if __name__ == "__main__":
    asyncio.run(main())
