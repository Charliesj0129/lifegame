import asyncio
import os
import sys

sys.path.append(os.getcwd())

from application.services.rich_menu_service import rich_menu_service

async def main():
    menu_id = "richmenu-06b731acf59c3536c035733107a224cf"
    image_path = "assets/rich_menu_v3.jpg"

    print(f"Uploading image to {menu_id}...")
    try:
        with open(image_path, "rb") as image:
            rich_menu_service.blob_api.set_rich_menu_image(
                rich_menu_id=menu_id,
                body=image.read(),
                _headers={"Content-Type": "image/jpeg"},
            )
        print(">>> Image Uploaded Successfully.")
        
        rich_menu_service.api.set_default_rich_menu(menu_id)
        print(f">>> Set Default Menu to: {menu_id}")
        
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
