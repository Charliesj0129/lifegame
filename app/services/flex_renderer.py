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
        # Cyberpunk Theme Colors
        COLOR_BG = "#0D1117"
        COLOR_ACCENT_GREEN = "#00FF9D" # Neon Green
        COLOR_ACCENT_RED = "#FF0055"   # Neon Red
        COLOR_TEXT_MAIN = "#E6EDF3"
        COLOR_TEXT_SUB = "#8B949E"
        
        # Calculate Stats for Bars (Simple normalization)
        # Assuming Level 10 is "Soft Cap" for visual width for now, or just /50
        def get_bar_width(val):
            return f"{min(int(val or 1), 100)}%"

        stats = [
            ("STR", user.str, "#FF5555"),
            ("INT", user.int, "#55AAFF"),
            ("VIT", user.vit, "#55FF55"),
            ("WIS", user.wis, "#AA55FF"),
            ("CHA", user.cha, "#FFFF55"),
        ]
        
        stat_rows = []
        for label, val, color in stats:
            stat_rows.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": label, "size": "xxs", "color": COLOR_TEXT_SUB, "flex": 1, "align": "center"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "flex": 4,
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "width": get_bar_width(val),
                                "height": "4px",
                                "backgroundColor": color,
                                "contents": []
                            }
                        ],
                        "backgroundColor": "#21262D",
                        "height": "4px",
                        "cornerRadius": "2px",
                        "margin": "sm",
                        "offsetTop": "4px"
                    },
                    {"type": "text", "text": str(val or 1), "size": "xxs", "color": COLOR_TEXT_MAIN, "flex": 1, "align": "end"}
                ],
                "margin": "xs"
            })

        # Hero Image (Dynamic Avatar Placeholder)
        hero_image = "https://images.unsplash.com/photo-1550751827-4bd374c3f58b" # Placeholder

        bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": "🔰 TACTICAL OS v2.0",
                        "weight": "bold",
                        "color": COLOR_ACCENT_GREEN,
                        "size": "xxs",
                        "flex": 1
                    },
                    {
                        "type": "text",
                        "text": f"ID: {user.id[:8]}",
                        "color": COLOR_TEXT_SUB,
                        "size": "xxs",
                        "align": "end",
                        "flex": 1
                    }
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg"
            },
            "hero": {
                 "type": "box",
                 "layout": "vertical",
                 "contents": [
                     {
                         "type": "box",
                         "layout": "horizontal",
                         "contents": [
                             {
                                 "type": "image",
                                 "url": hero_image,
                                 "size": "md",
                                 "aspectMode": "cover",
                                 "aspectRatio": "1:1",
                                 "cornerRadius": "100px",
                                 "flex": 0
                             },
                             {
                                 "type": "box",
                                 "layout": "vertical",
                                 "contents": [
                                     {"type": "text", "text": user.name or "Runner", "weight": "bold", "size": "lg", "color": COLOR_TEXT_MAIN},
                                     {"type": "text", "text": f"Level {user.level}", "size": "xs", "color": COLOR_ACCENT_RED, "weight": "bold"},
                                     {"type": "text", "text": f"Class: Novice", "size": "xxs", "color": COLOR_TEXT_SUB} 
                                 ],
                                 "flex": 1,
                                 "justifyContent": "center",
                                 "paddingStart": "md"
                             }
                         ],
                         "paddingAll": "lg"
                     }
                 ],
                 "backgroundColor": COLOR_BG
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                         "type": "separator",
                         "color": "#30363D"
                    },
                    # HP / Energy Bar
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                             {"type": "text", "text": "ENERGY (VIT)", "size": "xxs", "color": COLOR_TEXT_SUB, "margin": "md"},
                             {
                                 "type": "box",
                                 "layout": "horizontal",
                                 "contents": [
                                      {
                                          "type": "box",
                                          "layout": "vertical",
                                          "width": "100%", # Assuming Full for now
                                          "height": "6px",
                                          "backgroundColor": COLOR_ACCENT_GREEN,
                                          "contents": []
                                      }
                                 ],
                                 "backgroundColor": "#21262D",
                                 "height": "6px",
                                 "cornerRadius": "3px",
                                 "margin": "sm"
                             }
                        ]
                    },
                    # XP Bar
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                             {
                                 "type": "box",
                                 "layout": "horizontal",
                                 "contents": [
                                     {"type": "text", "text": "EXP", "size": "xxs", "color": COLOR_TEXT_SUB},
                                     {"type": "text", "text": f"{user.xp or 0} / 1000", "size": "xxs", "color": COLOR_TEXT_SUB, "align": "end"}
                                 ],
                                 "margin": "md"
                             },
                             {
                                 "type": "box",
                                 "layout": "horizontal",
                                 "contents": [
                                      {
                                          "type": "box",
                                          "layout": "vertical",
                                          "width": f"{min(((user.xp or 0)/1000)*100, 100)}%",
                                          "height": "6px",
                                          "backgroundColor": "#6e7681",
                                          "contents": []
                                      }
                                 ],
                                 "backgroundColor": "#21262D",
                                 "height": "6px",
                                 "cornerRadius": "3px",
                                 "margin": "sm"
                             }
                        ]
                    },
                    {
                        "type": "separator", 
                        "margin": "xl",
                        "color": "#30363D"
                    },
                    {
                        "type": "text", 
                        "text": "STATS MATRIX", 
                        "size": "xxs", 
                        "weight": "bold", 
                        "color": COLOR_TEXT_SUB, 
                        "margin": "lg",
                        "align": "center"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": stat_rows,
                        "margin": "md"
                    }
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg"
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "button", "action": {"type": "message", "label": "🎒 BAG", "text": "inventory"}, "style": "secondary", "height": "sm", "color": "#E6EDF3", "flex": 1},
                    {"type": "separator", "color": "transparent"}, 
                    {"type": "button", "action": {"type": "message", "label": "📜 QUESTS", "text": "quests"}, "style": "secondary", "height": "sm", "color": "#E6EDF3", "flex": 1}
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "md"
            }
        }
        
        return FlexMessage(
            alt_text=f"Tactical OS: {user.name}",
            contents=FlexContainer.from_dict(bubble)
        )

    def render_quest_list(self, quests: list) -> FlexMessage:
        COLOR_BG = "#0D1117"
        COLOR_ACCENT = "#00FF9D"
        
        COLOR_TIER_MAP = {
            "S": "#FF0055", # Red/Pink
            "A": "#FF5555", # Red
            "B": "#FFAA00", # Orange
            "C": "#FFFF55", # Yellow
            "D": "#55FF55", # Green
            "E": "#00FF9D", # Teal
            "F": "#8B949E"  # Gray
        }

        quest_rows = []
        for q in quests:
            status_icon = "✅" if q.status == "DONE" else "⬜"
            
            # Determine Color
            diff_color = COLOR_TIER_MAP.get(q.difficulty_tier, "#E6EDF3")
            
            # Loot Chance Logic (Simulated)
            loot_chance_text = ""
            if q.difficulty_tier in ["S", "A", "B"]:
                 chance = {"S": "50%", "A": "30%", "B": "15%"}.get(q.difficulty_tier, "10%")
                 loot_chance_text = f"🎲 Loot: {chance}"

            # Button or Status Text
            if q.status == "PENDING" or q.status == "ACTIVE":
                action_component = {
                    "type": "button",
                    "style": "primary",
                    "height": "sm",
                    "color": diff_color, # Match button to difficulty
                    "action": {
                        "type": "postback",
                        "label": "COMPLETE",
                        "data": f"action=complete_quest&quest_id={q.id}",
                        "displayText": f"Completing: {q.title}"
                    }
                }
            else:
                 action_component = {
                    "type": "text",
                    "text": "COMPLETED",
                    "color": "#8B949E",
                    "align": "center",
                    "size": "xs"
                }

            row_contents = [
                {
                    "type": "box",
                    "layout": "horizontal", 
                    "contents": [
                        {"type": "text", "text": f"[{q.difficulty_tier}] {q.title}", "weight": "bold", "color": diff_color, "flex": 1, "wrap": True},
                        {"type": "text", "text": f"+{q.xp_reward} XP", "color": "#FFD700", "size": "xs", "align": "end", "flex": 0}
                    ]
                },
                {
                    "type": "text",
                    "text": q.description or "No details.",
                    "size": "xxs",
                    "color": "#8B949E",
                    "wrap": True,
                    "margin": "xs"
                }
            ]
            
            # Add Loot Badge if high tier
            if loot_chance_text:
                row_contents.append({
                     "type": "text",
                     "text": loot_chance_text,
                     "size": "xxs",
                     "color": "#FFD700", # Gold
                     "margin": "xs"
                })

            row_contents.append({
                 "type": "box",
                 "layout": "vertical",
                 "contents": [action_component],
                 "margin": "md"
            })
            row_contents.append({"type": "separator", "margin": "md", "color": "#30363D"})

            row = {
                "type": "box",
                "layout": "vertical",
                "contents": row_contents,
                "margin": "lg"
            }
            quest_rows.append(row)
            
        if not quest_rows:
             quest_rows.append({
                 "type": "text", 
                 "text": "No active directives. Reroll?", 
                 "color": "#8B949E", 
                 "align": "center",
                 "margin": "lg"
             })

        bubble = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📜 ACTIVE DIRECTIVES", "weight": "bold", "color": COLOR_ACCENT, "size": "sm"}
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": quest_rows,
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg"
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "button", "action": {"type": "postback", "label": "♻️ REROLL", "data": "action=reroll_quests"}, "style": "secondary", "height": "sm", "color": "#E6EDF3"}
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "md"
            }
        }
        
        return FlexMessage(
            alt_text="Active Quests",
            contents=FlexContainer.from_dict(bubble)
        )

flex_renderer = FlexRenderer()
