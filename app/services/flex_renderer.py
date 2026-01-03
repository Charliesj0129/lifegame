from linebot.v3.messaging import FlexMessage, FlexContainer, TextMessage
from app.schemas.game_schemas import ProcessResult
from app.models.user import User

class FlexRenderer:
    def render(self, result: ProcessResult) -> FlexMessage:
        # Define Color Palette
        COLOR_PRIMARY = "#0D1117" # Dark Bg
        COLOR_ACCENT = "#00FF9D" # Neon Green
        COLOR_TEXT = "#E6EDF3"
        COLOR_WARN = "#FFD700"
        
        # Build JSON Bubble
        bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"ACTION LOGGED 🔥 x{result.streak_count}",
                        "weight": "bold",
                        "color": COLOR_ACCENT,
                        "size": "xxs"
                    }
                ],
                "backgroundColor": COLOR_PRIMARY,
                "paddingAll": "lg"
            },
            "hero": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{result.attribute} +{result.xp_gained}",
                        "size": "3xl", # Keeping it big
                        "weight": "bold",
                        "color": "#FFFFFF",
                        "align": "center"
                    },
                    {
                        "type": "text",
                        "text": result.user_title, # Show Identity Title
                        "size": "sm",
                        "color": "#8B949E", # Subtitle color
                        "align": "center",
                        "margin": "sm"
                    }
                ],
                "paddingAll": "none",
                "backgroundColor": COLOR_PRIMARY,
                "paddingBottom": "lg"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                     # Action Text
                    {
                        "type": "text",
                        "text": result.narrative or f"\"{result.action_text}\"",
                        "style": "normal",
                        "size": "sm",
                        "color": "#E6EDF3",
                        "wrap": True,
                        "align": "start",
                         "margin": "md"
                    },
                     # Level Info
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                             {"type": "text", "text": f"Lv.{result.new_level}", "color": COLOR_TEXT, "flex": 2, "weight": "bold"},
                             {"type": "text", "text": f"{result.current_xp} / {result.next_level_xp} XP", "color": "#8B949E", "size": "xs", "align": "end", "flex": 3}
                        ],
                        "margin": "xl"
                    },
                    # Progress Bar (Simulated with Box) - Simple calculation
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "width": f"{int(min((result.current_xp / result.next_level_xp)*100, 100))}%",
                                "height": "6px",
                                "backgroundColor": COLOR_ACCENT,
                                "contents": []
                            }
                        ],
                        "backgroundColor": "#30363D",
                        "height": "6px",
                        "cornerRadius": "3px",
                        "margin": "sm"
                    }
                ],
                "backgroundColor": COLOR_PRIMARY,
                "paddingAll": "lg"
            }
        }
        
        # Loot Section
        if result.loot_name:
             bubble["body"]["contents"].extend([
                 {
                     "type": "separator",
                     "margin": "lg",
                     "color": "#30363D"
                 },
                 {
                    "type": "text",
                    "text": "🎁 LOOT FOUND!",
                    "weight": "bold",
                    "color": COLOR_WARN, 
                    "margin": "lg",
                    "size": "xs"
                 },
                 {
                    "type": "text",
                    "text": f"[{result.loot_rarity}] {result.loot_name}",
                    "color": COLOR_TEXT,
                    "wrap": True,
                    "margin": "sm",
                    "size": "sm"
                 }
             ])
             
        # Level Up Animation/Text
        if result.leveled_up:
             bubble["header"]["contents"].append({
                 "type": "text",
                 "text": "🎉 LEVEL UP!",
                 "weight": "bold",
                 "color": "#FF79C6", 
                 "size": "sm",
                 "align": "end",
                 "position": "absolute",
                 "offsetEnd": "20px",
                 "offsetTop": "20px"
             })

        return FlexMessage(
            alt_text=result.to_text_message(),
            contents=FlexContainer.from_dict(bubble)
        )

    def render_status(self, user: User) -> FlexMessage:
        COLOR_PRIMARY = "#0D1117"
        COLOR_ACCENT = "#00FF9D"
        COLOR_TEXT = "#E6EDF3"
        
        # Calculate Stats for Bars (Simple normalization for visual)
        # Assuming max practical stat for bar is 100 for now
        stats = [
            ("STR", user.str, "#FF5555"),
            ("INT", user.int, "#55AAFF"),
            ("VIT", user.vit, "#55FF55"),
            ("WIS", user.wis, "#AA55FF"),
            ("CHA", user.cha, "#FFFF55"),
        ]
        
        stat_contents = []
        for label, val, color in stats:
            pct = min(val, 100) # Percentage width
            stat_contents.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": label, "size": "xs", "color": "#8B949E", "flex": 2},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "flex": 6,
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "width": f"{pct}%",
                                "height": "6px",
                                "backgroundColor": color,
                                "contents": []
                            }
                        ],
                        "backgroundColor": "#30363D",
                        "height": "6px",
                        "cornerRadius": "3px",
                        "margin": "sm",
                        "offsetTop": "3px" # Visual alignment
                    },
                    {"type": "text", "text": str(val), "size": "xs", "color": COLOR_TEXT, "flex": 1, "align": "end"}
                ],
                "margin": "sm"
            })

        bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": "STATUS CARD",
                        "weight": "bold",
                        "color": COLOR_ACCENT,
                        "size": "xxs"
                    },
                    {
                        "type": "text",
                        "text": f"Lv.{user.level}",
                        "weight": "bold",
                        "color": "#FFFFFF",
                        "size": "md",
                        "align": "end"
                    }
                ],
                "backgroundColor": COLOR_PRIMARY,
                "paddingAll": "lg"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                     {
                        "type": "text",
                        "text": user.name or "Adventurer",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#FFFFFF",
                        "align": "center",
                        "margin": "md"
                     },
                     {
                         "type": "separator",
                         "margin": "lg",
                         "color": "#30363D"
                     },
                     {
                         "type": "box",
                         "layout": "vertical",
                         "contents": stat_contents,
                         "margin": "lg"
                     }
                ],
                "backgroundColor": COLOR_PRIMARY,
                "paddingAll": "lg"
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                         "type": "text",
                         "text": f"Gold: {user.gold or 0} 🪙",
                         "color": "#FFD700",
                         "align": "center",
                         "size": "sm"
                    }
                ],
                "backgroundColor": COLOR_PRIMARY
            }
        }
        
        return FlexMessage(
            alt_text=f"Status: Lv.{user.level} {user.name}",
            contents=FlexContainer.from_dict(bubble)
        )

flex_renderer = FlexRenderer()
