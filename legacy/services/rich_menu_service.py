import json
import logging
from pathlib import Path
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
)
from app.core.config import settings

logger = logging.getLogger(__name__)

RICH_MENU_DATA_PATH = Path("data/rich_menus.json")


class RichMenuService:
    def __init__(self):
        if not settings.LINE_CHANNEL_ACCESS_TOKEN:
            logger.warning("LINE_CHANNEL_ACCESS_TOKEN not set. RichMenuService disabled.")
            self.api = None
            self.blob_api = None
        else:
            configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
            self.api_client = ApiClient(configuration)
            self.api = MessagingApi(self.api_client)
            self.blob_api = MessagingApiBlob(self.api_client)

    def _load_mappings(self):
        if RICH_MENU_DATA_PATH.exists():
            with open(RICH_MENU_DATA_PATH, "r") as f:
                return json.load(f)
        return {}

    def _save_mappings(self, data):
        RICH_MENU_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RICH_MENU_DATA_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def get_menu_id_by_name(self, name):
        """Fetches all rich menus and finds one with the matching name."""
        if not self.api:
            return None
        try:
            # Note: Pagination might be needed if > 1000 menus, but unlikely for this app.
            response = self.api.get_rich_menu_list()
            rich_menus = None
            for attr_name in ("richmenus", "rich_menus"):
                candidate = getattr(response, attr_name, None)
                if isinstance(candidate, (list, tuple)):
                    rich_menus = candidate
                    break
            if not rich_menus:
                logger.warning("Rich menu list response missing menus.")
                return None
            for menu in rich_menus:
                if menu.name == name:
                    return menu.rich_menu_id
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch rich menu list: {e}")
            return None

    def create_menu(self, name, areas, image_path=None, chat_bar_text=None):
        if not self.api:
            return None

        # 1. Idempotency Check
        existing_id = self.get_menu_id_by_name(name)
        if existing_id:
            logger.info(f"Rich Menu '{name}' already exists ({existing_id}). Skipping creation.")
            return existing_id

        # 2. Create Object
        req = RichMenuRequest(
            size=RichMenuSize(width=2500, height=1686),
            selected=False,  # Don't auto-open
            name=name,
            chat_bar_text=chat_bar_text or name.upper(),
            areas=areas,
        )
        try:
            rich_menu_id = self.api.create_rich_menu(rich_menu_request=req).rich_menu_id
            logger.info(f"Created Rich Menu '{name}': {rich_menu_id}")

            # 3. Upload Image
            if image_path:
                try:
                    with open(image_path, "rb") as image:
                        self.blob_api.set_rich_menu_image(
                            rich_menu_id=rich_menu_id,
                            body=image.read(),
                            _headers={"Content-Type": "image/jpeg"},
                        )
                    logger.info(f"Uploaded image for '{name}'")
                except FileNotFoundError:
                    logger.warning(f"Image path {image_path} not found. Menu created without image.")

            return rich_menu_id

        except Exception as e:
            logger.error(f"Failed to create menu '{name}': {e}")
            return None

    def setup_menus(self):
        """Creates Standard Menus if they don't exist."""

        # Define Layouts
        def get_main_areas():
            buttons = [
                MessageAction(label="狀態", text="狀態"),
                MessageAction(label="任務", text="任務"),
                MessageAction(label="背包", text="背包"),
                MessageAction(label="商店", text="商店"),
                MessageAction(label="合成", text="合成"),
                MessageAction(label="首領", text="首領"),
                MessageAction(label="攻擊", text="攻擊"),
                MessageAction(label="簽到", text="簽到"),
                PostbackAction(
                    label="重新生成",
                    data="action=reroll_quests",
                    display_text="重新生成任務",
                ),
                PostbackAction(
                    label="全部接受",
                    data="action=accept_all_quests",
                    display_text="全部接受任務",
                ),
                PostbackAction(
                    label="略過 Viper",
                    data="action=skip_rival_update",
                    display_text="略過 Viper 更新",
                ),
                MessageAction(label="指令", text="指令"),
            ]

            areas = []
            cols = 4
            rows = 3
            width = 2500
            height = 1686
            cell_w = width // cols
            cell_h = height // rows

            for idx, action in enumerate(buttons):
                row = idx // cols
                col = idx % cols
                areas.append(
                    RichMenuArea(
                        bounds=RichMenuBounds(
                            x=col * cell_w,
                            y=row * cell_h,
                            width=cell_w,
                            height=cell_h,
                        ),
                        action=action,
                    )
                )

            return areas

        # Define Menus to Create
        menus = {
            "MAIN": {
                "name": "LIFGAME_MAIN_V2",
                "areas": get_main_areas(),
                "image": "assets/rich_menu.jpg",
                "chat_bar_text": "操作面板",
            }
        }

        mappings = {}
        for key, config in menus.items():
            mid = self.create_menu(
                config["name"],
                config["areas"],
                config["image"],
                chat_bar_text=config.get("chat_bar_text"),
            )
            if mid:
                mappings[key] = mid

        self._save_mappings(mappings)
        return mappings

    def link_user(self, user_id, mode):
        if not self.api:
            return
        mappings = self._load_mappings()
        menu_id = mappings.get(mode)
        if menu_id:
            try:
                self.api.link_rich_menu_to_user(user_id, menu_id)
                logger.info(f"Linked {user_id} to {mode} ({menu_id})")
            except Exception as e:
                logger.error(f"Link failed: {e}")


rich_menu_service = RichMenuService()
