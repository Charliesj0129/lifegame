from linebot.v3.messaging import FlexMessage, FlexContainer, TextMessage
from app.schemas.game_schemas import ProcessResult
from app.models.user import User

class FlexRenderer:
    def render(self, result: ProcessResult) -> FlexMessage:
        COLOR_BG = "#0B0F14"
        COLOR_PANEL = "#111827"
        COLOR_ACCENT = "#7DF9FF"
        COLOR_TEXT = "#E6EDF3"
        COLOR_MUTED = "#8B949E"
        COLOR_LINE = "#243041"
        COLOR_LOOT = "#F5C542"
        COLOR_BADGE_TEXT = "#0B0F14"

        difficulty = getattr(result, "difficulty_tier", None) or "E"
        tier_colors = {
            "S": "#FF3B6B",
            "A": "#FF6B6B",
            "B": "#FFB020",
            "C": "#F6D365",
            "D": "#5CDE7A",
            "E": "#20D6C7",
            "F": "#8B949E"
        }
        diff_color = tier_colors.get(difficulty, COLOR_ACCENT)

        loot_chance_map = {
            "S": 80,
            "A": 60,
            "B": 40,
            "C": 30,
            "D": 24,
            "E": 20,
            "F": 10
        }
        loot_chance = loot_chance_map.get(difficulty, 20)

        next_level_xp = result.next_level_xp or 1
        progress_pct = int(min((result.current_xp / next_level_xp) * 100, 100))

        header_row = {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": "LIFEGAME / ACTION TICKET",
                    "size": "xxs",
                    "weight": "bold",
                    "color": COLOR_ACCENT,
                    "flex": 1,
                    "wrap": True
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"TIER {difficulty}",
                            "size": "xxs",
                            "weight": "bold",
                            "color": COLOR_BADGE_TEXT,
                            "align": "center"
                        }
                    ],
                    "backgroundColor": diff_color,
                    "paddingAll": "xs",
                    "cornerRadius": "12px",
                    "flex": 0
                }
            ]
        }

        header_meta = {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"🔥 STREAK x{result.streak_count}",
                            "size": "xxs",
                            "weight": "bold",
                            "color": COLOR_ACCENT
                        }
                    ],
                    "backgroundColor": COLOR_PANEL,
                    "paddingStart": "sm",
                    "paddingEnd": "sm",
                    "paddingTop": "xs",
                    "paddingBottom": "xs",
                    "cornerRadius": "12px",
                    "flex": 0
                },
                {
                    "type": "text",
                    "text": f"DROP {loot_chance}%",
                    "size": "xxs",
                    "color": COLOR_LOOT,
                    "align": "end",
                    "flex": 1
                }
            ],
            "margin": "sm"
        }

        bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [header_row, header_meta],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg"
            },
            "hero": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{result.attribute} +{result.xp_gained}",
                        "size": "3xl",
                        "weight": "bold",
                        "color": COLOR_TEXT,
                        "align": "center"
                    },
                    {
                        "type": "text",
                        "text": result.user_title,
                        "size": "xs",
                        "color": COLOR_MUTED,
                        "align": "center",
                        "margin": "xs"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": f"LV {result.new_level}", "color": COLOR_TEXT, "size": "sm", "weight": "bold", "flex": 0},
                            {"type": "text", "text": f"{result.current_xp}/{next_level_xp} XP", "color": COLOR_MUTED, "size": "xxs", "align": "end", "flex": 1}
                        ],
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "width": f"{progress_pct}%",
                                "height": "6px",
                                "backgroundColor": COLOR_ACCENT,
                                "contents": []
                            }
                        ],
                        "backgroundColor": COLOR_LINE,
                        "height": "6px",
                        "cornerRadius": "3px",
                        "margin": "sm"
                    }
                ],
                "backgroundColor": COLOR_PANEL,
                "paddingAll": "lg"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": result.narrative or f"\"{result.action_text}\"",
                        "style": "normal",
                        "size": "sm",
                        "color": COLOR_TEXT,
                        "wrap": True,
                        "align": "start",
                        "margin": "md"
                    },
                    {"type": "separator", "margin": "md", "color": COLOR_LINE}
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg"
            }
        }

        if result.leveled_up:
            bubble["body"]["contents"].append({
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "LEVEL UP",
                        "size": "xs",
                        "weight": "bold",
                        "color": COLOR_BADGE_TEXT,
                        "align": "center"
                    }
                ],
                "backgroundColor": "#FFD166",
                "cornerRadius": "12px",
                "paddingAll": "sm",
                "margin": "md"
            })

        if result.loot_name:
            bubble["body"]["contents"].extend([
                {"type": "separator", "margin": "md", "color": COLOR_LINE},
                {
                    "type": "text",
                    "text": "🎁 LOOT FOUND",
                    "weight": "bold",
                    "color": COLOR_LOOT,
                    "margin": "md",
                    "size": "xs"
                },
                {
                    "type": "text",
                    "text": f"[{result.loot_rarity}] {result.loot_name}",
                    "color": COLOR_TEXT,
                    "wrap": True,
                    "margin": "xs",
                    "size": "sm"
                }
            ])

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
                "spacing": "sm",
                "contents": [
                    {"type": "button", "action": {"type": "message", "label": "🎒 BAG", "text": "inventory"}, "style": "secondary", "height": "sm", "color": "#E6EDF3", "flex": 1},
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

    def render_shop_list(self, items: list, user_gold: int) -> FlexMessage:
        COLOR_BG = "#0D1117"
        COLOR_ACCENT = "#F5C542" # Gold
        
        item_rows = []
        for item in items:
            row = {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": item.name, "weight": "bold", "color": "#E6EDF3", "size": "sm"},
                            {"type": "text", "text": f"{item.price} G", "color": COLOR_ACCENT, "size": "xs"}
                        ],
                        "flex": 1
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": "#238636", # Green
                        "action": {
                            "type": "postback",
                            "label": "BUY",
                            "data": f"action=buy_item&item_id={item.id}",
                            "displayText": f"Buying {item.name}"
                        },
                        "flex": 0
                    }
                ],
                "margin": "md",
                "alignItems": "center"
            }
            item_rows.append(row)
            item_rows.append({"type": "separator", "margin": "md", "color": "#30363D"})
            
        if not item_rows:
            item_rows.append({"type": "text", "text": "Shop is empty.", "color": "#8B949E", "align": "center"})
            
        bubble = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "🛒 BLACK MARKET", "weight": "bold", "color": COLOR_ACCENT, "size": "md"},
                    {"type": "text", "text": f"Balance: {user_gold} G", "color": "#E6EDF3", "size": "xs", "align": "end"}
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": item_rows,
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg"
            }
        }
        
        return FlexMessage(
            alt_text="Cycle Shop",
            contents=FlexContainer.from_dict(bubble)
        )

    def render_crafting_menu(self, recipes: list) -> FlexMessage:
        COLOR_BG = "#0D1117"
        COLOR_ACCENT = "#D2A8FF" # Purple
        
        recipe_rows = []
        for r_data in recipes:
            recipe = r_data['recipe']
            can_craft = r_data['can_craft']
            missing = r_data['missing']
            
            # Button Logic
            if can_craft:
                action_btn = {
                    "type": "button",
                    "style": "primary",
                    "height": "sm",
                    "color": COLOR_ACCENT,
                    "action": {
                        "type": "postback",
                        "label": "CRAFT",
                        "data": f"action=craft&recipe_id={recipe.id}",
                        "displayText": f"Crafting {recipe.name}"
                    },
                    "flex": 0
                }
                status_text = {"type": "text", "text": "✅ Ready", "size": "xxs", "color": "#00FF9D"}
            else:
                action_btn = {
                     "type": "button",
                     "style": "secondary",
                     "height": "sm",
                     "color": "#30363D",
                     "action": {
                         "type": "postback",
                         "label": "LOCKED",
                         "data": "action=noop",
                     },
                     "flex": 0
                }
                status_text = {"type": "text", "text": f"❌ Missing: {', '.join(missing)}", "size": "xxs", "color": "#FF5555", "wrap": True}

            row = {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                         "type": "box",
                         "layout": "horizontal",
                         "contents": [
                             {"type": "text", "text": recipe.name, "weight": "bold", "color": "#E6EDF3", "size": "sm", "flex": 1},
                             action_btn
                         ],
                         "alignItems": "center"
                    },
                    status_text,
                    {"type": "separator", "margin": "md", "color": "#30363D"}
                ],
                "margin": "md"
            }
            recipe_rows.append(row)
            
        if not recipe_rows:
            recipe_rows.append({"type": "text", "text": "No known recipes.", "color": "#8B949E", "align": "center"})

        bubble = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "⚒️ WORKSHOP", "weight": "bold", "color": COLOR_ACCENT, "size": "md"},
                    {"type": "text", "text": "Combine ingredients to create items.", "color": "#8B949E", "size": "xs"}
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": recipe_rows,
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg"
            }
        }
        
        return FlexMessage(
            alt_text="Crafting Workshop",
            contents=FlexContainer.from_dict(bubble)
        )

    def render_boss_status(self, boss) -> FlexMessage:
        if not boss:
             # Fallback Message
            return TextMessage(text="No active boss. Type 'Boss' to summon one.")
            
        # Calc HP Bar
        percentage = int((boss.hp / boss.max_hp) * 100)
        bar_color = "#00FF9D" if percentage > 50 else "#FF5555"
        
        bubble = {
            "type": "bubble",
            "size": "giga",
            "body": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#0D1117",
                "contents": [
                    {"type": "text", "text": "☠️ BOSS BATTLE", "weight": "bold", "color": "#FF5555", "size": "sm"},
                    {"type": "text", "text": boss.name, "weight": "bold", "color": "#FFFFFF", "size": "xl", "margin": "sm"},
                    {"type": "text", "text": f"Lv.{boss.level}", "color": "#8B949E", "size": "xs"},
                    
                    # HP Bar Container
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "backgroundColor": "#30363D",
                        "cornerRadius": "md",
                        "height": "10px",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "backgroundColor": bar_color,
                                "width": f"{percentage}%",
                                "height": "10px",
                                "cornerRadius": "md"
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                             {"type": "text", "text": f"HP: {boss.hp}/{boss.max_hp}", "size": "xs", "color": "#E6EDF3"},
                             {"type": "text", "text": f"{percentage}%", "size": "xs", "color": "#E6EDF3", "align": "end"}
                        ],
                        "margin": "sm"
                    },
                    
                    {"type": "separator", "margin": "md", "color": "#30363D"},
                    
                    # Actions
                    {
                         "type": "box",
                         "layout": "horizontal",
                         "margin": "md",
                         "spacing": "sm",
                         "contents": [
                             {
                                 "type": "button",
                                 "style": "primary",
                                 "color": "#FF5555",
                                 "action": {
                                     "type": "message",
                                     "label": "⚔️ ATTACK",
                                     "text": "Attack"
                                 }
                             }
                         ]
                    }
                ],
                "paddingAll": "lg"
            }
        }
        
        return FlexMessage(
            alt_text=f"Boss: {boss.name}",
            contents=FlexContainer.from_dict(bubble)
        )

flex_renderer = FlexRenderer()
