import sys
import os
# Add project root to path
sys.path.append(os.getcwd())

from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    RichMenuRequest,
    RichMenuArea,
    RichMenuBounds,
    RichMenuSize,
    PostbackAction,
    MessageAction,
    URIAction
)
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("setup_rich_menu")

def setup():
    if not settings.LINE_CHANNEL_ACCESS_TOKEN:
        logger.error("LINE_CHANNEL_ACCESS_TOKEN not set.")
        return

    configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_blob_api = MessagingApiBlob(api_client)

        # 1. Create Rich Menu Object
        rich_menu_to_create = RichMenuRequest(
            size=RichMenuSize(width=2500, height=1686),
            selected=True,
            name="Main Menu",
            chat_bar_text="Open Menu",
            areas=[
                # Status (Top Left)
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
                    action=MessageAction(label="Status", text="Status")
                ),
                # Inventory (Top Right)
                RichMenuArea(
                    bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
                    action=MessageAction(label="Inventory", text="Inventory")
                ),
                # Help (Bottom)
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=843, width=2500, height=843),
                    action=URIAction(label="Help", uri="https://github.com/your-repo/lifgame") # Or MessageAction text="Help"
                )
            ]
        )

        rich_menu_id = messaging_api.create_rich_menu(rich_menu_request=rich_menu_to_create).rich_menu_id
        logger.info(f"Created Rich Menu ID: {rich_menu_id}")

        # 2. Upload Image
        with open("assets/rich_menu.jpg", "rb") as image:
            # Note: The image needs to be the correct aspect ratio/size. 
            # If the generated image is square, it might stretch or have issues.
            # But we will upload it anyway.
            messaging_blob_api.set_rich_menu_image(
                rich_menu_id=rich_menu_id,
                body=image.read(),
                _headers={'Content-Type': 'image/jpeg'}
            )
        logger.info("Uploaded Image.")

        # 3. Set Default
        messaging_api.set_default_rich_menu(rich_menu_id=rich_menu_id)
        logger.info("Set as Default Rich Menu.")

if __name__ == "__main__":
    setup()
