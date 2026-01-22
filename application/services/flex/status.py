from linebot.v3.messaging import FlexContainer, FlexMessage

from app.models.user import User


class FlexStatusRenderer:
    def render_status(self, user: User, lore_progress: list = None) -> FlexMessage:
        # Robust attribute retrieval with defaults
        current_hp = getattr(user, "hp", 100)
        if current_hp is None:
            current_hp = 100
        max_hp = getattr(user, "max_hp", 100) or 100

        # Attributes with SAFE defaults
        str_val = getattr(user, "str", 1) or 1
        int_val = getattr(user, "int", 1) or 1
        vit_val = getattr(user, "vit", 1) or 1
        wis_val = getattr(user, "wis", 1) or 1
        cha_val = getattr(user, "cha", 1) or 1

        user_level = getattr(user, "level", 1) or 1
        job_class = getattr(user, "job_class", "Novice") or "Novice"
        user_name = getattr(user, "name", "User") or "User"

        # Calculate derived stats
        # xp_next = lvl * 100
        # xp_pct = int((xp / xp_next) * 100) if xp_next > 0 else 0 (Unused)

        hp_pct = int((current_hp / max_hp) * 100) if max_hp > 0 else 0
        COLOR_BG = "#0B0F14"
        COLOR_PANEL = "#161B22"
        COLOR_ACCENT = "#7DF9FF"
        COLOR_TEXT = "#E6EDF3"
        COLOR_MUTED = "#8B949E"
        COLOR_HP_GOOD = "#3FB950"
        COLOR_HP_LOW = "#F85149"

        hp_color = COLOR_HP_GOOD if hp_pct > 30 else COLOR_HP_LOW

        bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "STATUS WINDOW",
                        "weight": "bold",
                        "color": COLOR_ACCENT,
                        "size": "xxs",
                        "letterSpacing": "1px"
                    },
                    {
                        "type": "text",
                        "text": user_name,
                        "weight": "bold",
                        "size": "3xl",
                        "color": COLOR_TEXT,
                        "margin": "md"
                    },
                    {
                        "type": "text",
                        "text": f"Lv.{user_level} {job_class}",
                        "size": "sm",
                        "color": COLOR_MUTED,
                        "margin": "xs"
                    }
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    # Visual HP Bar with Label
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {"type": "text", "text": "HP", "size": "xs", "weight": "bold", "color": COLOR_HP_GOOD, "flex": 0},
                                    {"type": "text", "text": f"{current_hp}/{max_hp}", "size": "xs", "color": COLOR_TEXT, "align": "end", "flex": 1}
                                ],
                                "margin": "xs"
                            },
                            {
                                "type": "box",
                                "layout": "vertical",
                                "width": "100%",
                                "height": "8px",
                                "backgroundColor": "#30363D",
                                "cornerRadius": "4px",
                                "margin": "sm",
                                "contents": [
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "width": f"{hp_pct}%",
                                        "height": "8px",
                                        "backgroundColor": hp_color,
                                        "cornerRadius": "4px",
                                        "contents": []
                                    }
                                ]
                            }
                        ],
                        "backgroundColor": COLOR_PANEL,
                        "paddingAll": "md",
                        "cornerRadius": "12px"
                    },
                    # Stats Grid
                    {
                        "type": "text",
                        "text": "ATTRIBUTES",
                        "size": "xxs",
                        "weight": "bold",
                        "color": COLOR_MUTED,
                        "margin": "xl"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "md",
                        "contents": [
                            # Column 1
                            {
                                "type": "box",
                                "layout": "vertical",
                                "flex": 1,
                                "contents": [
                                    {"type": "text", "text": f"STR  {str_val}", "size": "sm", "color": COLOR_TEXT, "margin": "sm", "weight": "bold"},
                                    {"type": "text", "text": f"INT  {int_val}", "size": "sm", "color": COLOR_TEXT, "margin": "sm", "weight": "bold"},
                                    {"type": "text", "text": f"VIT  {vit_val}", "size": "sm", "color": COLOR_TEXT, "margin": "sm", "weight": "bold"},
                                ]
                            },
                            # Column 2
                            {
                                "type": "box",
                                "layout": "vertical",
                                "flex": 1,
                                "contents": [
                                    {"type": "text", "text": f"WIS  {wis_val}", "size": "sm", "color": COLOR_TEXT, "margin": "sm", "weight": "bold"},
                                    {"type": "text", "text": f"CHA  {cha_val}", "size": "sm", "color": COLOR_TEXT, "margin": "sm", "weight": "bold"},
                                    {"type": "text", "text": " ", "size": "sm", "margin": "sm"}, # Spacer
                                ]
                            }
                        ]
                    }
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg"
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {"type": "postback", "label": "REFRESH", "data": "action=status"},
                        "style": "secondary",
                        "height": "sm",
                        "color": COLOR_ACCENT
                    }
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "md"
            }
        }

        return FlexMessage(alt_text="Status Window", contents=FlexContainer.from_dict(bubble))


status_renderer = FlexStatusRenderer()
