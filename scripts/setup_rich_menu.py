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
    except Exception as e:
        print(f"FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(main())
