import asyncio
import os
import sys

# Ensure app is in path
sys.path.append(os.getcwd())

from application.services.rich_menu_service import rich_menu_service


async def main():
    print(">>> Setting up Rich Menus...")
    try:
        mappings = rich_menu_service.setup_menus()
        print(f">>> Rich Menus Created: {mappings}")

        # Set Default to MAIN
        if "MAIN" in mappings:
            main_id = mappings["MAIN"]
            rich_menu_service.api.set_default_rich_menu(main_id)
            print(f">>> Set Default Menu to: {main_id}")
    except Exception as e:
        print(f"FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(main())
