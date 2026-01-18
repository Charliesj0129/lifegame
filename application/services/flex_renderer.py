import datetime
from linebot.v3.messaging import FlexMessage, FlexContainer, TextMessage
from app.schemas.game_schemas import ProcessResult
from app.models.user import User


COLOR_BG = "#0B0F14"
COLOR_PANEL = "#111827"
COLOR_ACCENT = "#7DF9FF"
COLOR_TEXT = "#E6EDF3"
COLOR_MUTED = "#8B949E"
COLOR_LINE = "#243041"
COLOR_LOOT = "#F5C542"
COLOR_BADGE_TEXT = "#0B0F14"
COLOR_REWARD = "#FACC15"


class FlexRenderer:
    def render_shop(self, items: list) -> FlexMessage:
        """Renders the Shop Item list."""
        bubble = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "🛒 黑市交易", "weight": "bold", "color": COLOR_ACCENT, "size": "xl"},
                    {"type": "text", "text": "每日限量供應", "color": COLOR_MUTED, "size": "xs"},
                ],
                "backgroundColor": COLOR_BG,
            },
            "body": {"type": "box", "layout": "vertical", "contents": []},
        }

        for item in items:
            row = {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": item.name, "color": COLOR_TEXT, "flex": 1, "weight": "bold"},
                    {"type": "text", "text": f"{item.price} G", "color": COLOR_LOOT, "flex": 0, "size": "sm"},
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {"type": "postback", "label": "購買", "data": f"action=buy_item&item_id={item.id}"},
                    },
                ],
                "margin": "md",
                "alignItems": "center",
            }
            bubble["body"]["contents"].append(row)

        return FlexMessage(alt_text="商店清單", contents=FlexContainer.from_dict(bubble))

    def render(self, result: ProcessResult) -> FlexMessage:
        tier_colors = {
            "S": "#FF3B6B",
            "A": "#FF6B6B",
            "B": "#FFB020",
            "C": "#F6D365",
            "D": "#5CDE7A",
            "E": "#20D6C7",
            "F": "#8B949E",
        }
        difficulty = result.difficulty_tier or "E"
        diff_color = tier_colors.get(difficulty, COLOR_ACCENT)

        loot_chance_map = {
            "S": 80,
            "A": 60,
            "B": 40,
            "C": 30,
            "D": 24,
            "E": 20,
            "F": 10,
        }
        loot_chance = loot_chance_map.get(difficulty, 20)

        next_level_xp = result.next_level_xp or 1
        progress_pct = int(min((result.current_xp / next_level_xp) * 100, 100))
        streak_count = max(result.streak_count or 0, 0)

        attr_map = {
            "STR": "力量",
            "INT": "智力",
            "VIT": "體力",
            "WIS": "智慧",
            "CHA": "魅力",
        }
        attr_label = attr_map.get(result.attribute, result.attribute or "能力")
        user_title = result.user_title or "行動者"

        rarity_map = {
            "COMMON": "普通",
            "UNCOMMON": "進階",
            "RARE": "稀有",
            "EPIC": "史詩",
            "LEGENDARY": "傳說",
        }
        loot_rarity_key = (result.loot_rarity or "").upper()
        loot_rarity_label = rarity_map.get(loot_rarity_key, result.loot_rarity or "")
        action_text = result.action_text or result.text or ""

        header_row = {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": "戰術系統｜全像票證",
                    "size": "xxs",
                    "weight": "bold",
                    "color": COLOR_ACCENT,
                    "flex": 1,
                    "wrap": True,
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"難度 {difficulty}",
                            "size": "xxs",
                            "weight": "bold",
                            "color": COLOR_BADGE_TEXT,
                            "align": "center",
                        }
                    ],
                    "backgroundColor": diff_color,
                    "paddingAll": "xs",
                    "cornerRadius": "12px",
                    "flex": 0,
                },
            ],
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
                            "text": f"連續 {streak_count} 天",
                            "size": "xxs",
                            "weight": "bold",
                            "color": COLOR_ACCENT,
                        }
                    ],
                    "backgroundColor": COLOR_PANEL,
                    "paddingStart": "sm",
                    "paddingEnd": "sm",
                    "paddingTop": "xs",
                    "paddingBottom": "xs",
                    "cornerRadius": "12px",
                    "flex": 0,
                },
                {
                    "type": "text",
                    "text": f"掉落率 {loot_chance}%",
                    "size": "xxs",
                    "color": COLOR_LOOT,
                    "align": "end",
                    "flex": 1,
                },
            ],
            "margin": "sm",
        }

        bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [header_row, header_meta],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "hero": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{attr_label} +{result.xp_gained} 經驗",
                        "size": "3xl",
                        "weight": "bold",
                        "color": COLOR_TEXT,
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": user_title,
                        "size": "xs",
                        "color": COLOR_MUTED,
                        "align": "center",
                        "margin": "xs",
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"等級 {result.new_level}",
                                "color": COLOR_TEXT,
                                "size": "sm",
                                "weight": "bold",
                                "flex": 0,
                            },
                            {
                                "type": "text",
                                "text": f"{result.current_xp}/{next_level_xp} 經驗",
                                "color": COLOR_MUTED,
                                "size": "xxs",
                                "align": "end",
                                "flex": 1,
                            },
                        ],
                        "margin": "md",
                    },
                    {
                        "type": "text",
                        "text": "等級進度",
                        "size": "xxs",
                        "color": COLOR_MUTED,
                        "align": "start",
                        "margin": "md",
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
                                "contents": [],
                            }
                        ],
                        "backgroundColor": COLOR_LINE,
                        "height": "6px",
                        "cornerRadius": "3px",
                        "margin": "sm",
                    },
                ],
                "backgroundColor": COLOR_PANEL,
                "paddingAll": "lg",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "行動紀錄",
                        "size": "xs",
                        "weight": "bold",
                        "color": COLOR_ACCENT,
                        "margin": "md",
                    },
                    {
                        "type": "text",
                        "text": result.narrative or f"「{action_text}」",
                        "style": "normal",
                        "size": "sm",
                        "color": COLOR_TEXT,
                        "wrap": True,
                        "align": "start",
                        "margin": "sm",
                    },
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
        }

        if result.narrative and action_text:
            bubble["body"]["contents"].append(
                {
                    "type": "text",
                    "text": f"「{action_text}」",
                    "style": "normal",
                    "size": "xxs",
                    "color": COLOR_MUTED,
                    "wrap": True,
                    "align": "start",
                    "margin": "xs",
                }
            )

        bubble["body"]["contents"].append({"type": "separator", "margin": "md", "color": COLOR_LINE})

        if result.leveled_up:
            bubble["body"]["contents"].append(
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "等級提升",
                            "size": "xs",
                            "weight": "bold",
                            "color": COLOR_BADGE_TEXT,
                            "align": "center",
                        }
                    ],
                    "backgroundColor": "#FFD166",
                    "cornerRadius": "12px",
                    "paddingAll": "sm",
                    "margin": "md",
                }
            )

        if result.loot_name:
            bubble["body"]["contents"].extend(
                [
                    {"type": "separator", "margin": "md", "color": COLOR_LINE},
                    {
                        "type": "text",
                        "text": "🎁 戰利品掉落",
                        "weight": "bold",
                        "color": COLOR_LOOT,
                        "margin": "md",
                        "size": "xs",
                    },
                    {
                        "type": "text",
                        "text": f"{loot_rarity_label}｜{result.loot_name}",
                        "color": COLOR_TEXT,
                        "wrap": True,
                        "margin": "xs",
                        "size": "sm",
                    },
                ]
            )

        return FlexMessage(alt_text=result.to_text_message(), contents=FlexContainer.from_dict(bubble))

    def render_status(self, user: User, lore_progress: list = None) -> FlexMessage:
        if lore_progress is None:
            lore_progress = []
        from application.services.flex.status import status_renderer as sub_renderer

        return sub_renderer.render_status(user, lore_progress)

    def render_lore_shard(self, shard) -> FlexMessage:
        return FlexMessage(
            alt_text=f"檔案解鎖：{shard.title}",
            contents=FlexContainer.from_dict(
                {
                    "type": "bubble",
                    "size": "mega",
                    "header": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "📂 檔案解密成功",
                                "weight": "bold",
                                "color": COLOR_ACCENT,
                                "size": "xs",
                            }
                        ],
                        "backgroundColor": "#0D1117",
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": shard.title,
                                "weight": "bold",
                                "size": "lg",
                                "color": COLOR_TEXT,
                            },
                            {
                                "type": "text",
                                "text": f"系列：{shard.series}｜第 {shard.chapter} 章",
                                "size": "xs",
                                "color": COLOR_MUTED,
                                "margin": "sm",
                            },
                            {"type": "separator", "margin": "md", "color": "#30363D"},
                            {
                                "type": "text",
                                "text": shard.body,
                                "size": "sm",
                                "color": COLOR_TEXT,
                                "wrap": True,
                                "margin": "md",
                                "style": "italic",
                            },
                        ],
                        "backgroundColor": "#161B22",
                    },
                }
            ),
        )

    def render_quest_list(self, quests: list, habits: list = None) -> FlexMessage:
        COLOR_CARD = "#151C2B"
        COLOR_TIER_MAP = {
            "S": "#FF3B6B",
            "A": "#FF5C8A",
            "B": "#FFB020",
            "C": "#F6D365",
            "D": "#4ADE80",
            "E": "#22D3EE",
            "F": "#94A3B8",
        }

        loot_chance_map = {"S": 50, "A": 30, "B": 15, "C": 10, "D": 8, "E": 5, "F": 3}

        verification_labels = {
            "TEXT": "📝 文字回報",
            "IMAGE": "📷 照片驗證",
            "LOCATION": "📍 位置驗證",
        }

        today = datetime.date.today()
        habit_rows = []
        if habits:
            for h in habits:
                tier = getattr(h, "tier", "T1")
                streak = getattr(h, "zone_streak_days", 0) or 0
                habit_label = getattr(h, "habit_name", None) or getattr(h, "habit_tag", None) or "習慣"
                done_today = getattr(h, "last_outcome_date", None) == today

                if done_today:
                    action_component = {
                        "type": "text",
                        "text": "✅ 今日已打卡",
                        "color": "#22C55E",
                        "align": "center",
                        "size": "xs",
                    }
                else:
                    action_component = {
                        "type": "button",
                        "style": "primary",
                        "color": "#22D3EE",
                        "height": "sm",
                        "action": {
                            "type": "postback",
                            "label": "打卡",
                            "data": f"action=check_habit&habit_id={h.id}",
                            "displayText": f"習慣打卡：{habit_label}",
                        },
                    }

                row = {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": COLOR_CARD,
                    "cornerRadius": "12px",
                    "paddingAll": "md",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "🔄", "size": "sm", "flex": 0},
                                {
                                    "type": "text",
                                    "text": habit_label,
                                    "weight": "bold",
                                    "color": COLOR_TEXT,
                                    "size": "sm",
                                    "flex": 1,
                                    "wrap": True,
                                    "margin": "sm",
                                },
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": tier,
                                            "size": "xxs",
                                            "weight": "bold",
                                            "color": COLOR_TEXT,
                                            "align": "center",
                                        }
                                    ],
                                    "backgroundColor": COLOR_PANEL,
                                    "cornerRadius": "8px",
                                    "paddingAll": "xs",
                                    "flex": 0,
                                },
                            ],
                            "alignItems": "center",
                        },
                        {
                            "type": "text",
                            "text": f"連續 {streak} 天｜例行打卡",
                            "color": COLOR_MUTED,
                            "size": "xs",
                            "margin": "sm",
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [action_component],
                            "margin": "md",
                        },
                    ],
                }
                habit_rows.append(row)

        quest_rows = []
        for q in quests:
            diff_color = COLOR_TIER_MAP.get(q.difficulty_tier, COLOR_TEXT)
            loot_chance_text = ""
            if q.difficulty_tier in loot_chance_map:
                loot_chance_text = f"🎲 掉落率 {loot_chance_map.get(q.difficulty_tier)}%"

            verification_type = (q.verification_type or "").upper()
            verification_hint = verification_labels.get(verification_type)

            if q.status == "PENDING" or q.status == "ACTIVE":
                if verification_type == "TEXT":
                    action_component = {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": diff_color,
                        "action": {
                            "type": "message",
                            "label": "回報文字",
                            "text": f"回報：{q.title}",
                        },
                    }
                elif verification_type == "IMAGE":
                    action_component = {
                        "type": "text",
                        "text": "📷 請直接上傳照片完成驗證",
                        "color": COLOR_MUTED,
                        "align": "center",
                        "size": "xs",
                    }
                elif verification_type == "LOCATION":
                    action_component = {
                        "type": "text",
                        "text": "📍 請分享位置完成驗證",
                        "color": COLOR_MUTED,
                        "align": "center",
                        "size": "xs",
                    }
                else:
                    action_component = {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": diff_color,
                        "action": {
                            "type": "postback",
                            "label": "完成",
                            "data": f"action=complete_quest&quest_id={q.id}",
                            "displayText": f"完成任務：{q.title}",
                        },
                    }
            else:
                action_component = {
                    "type": "text",
                    "text": "已完成",
                    "color": COLOR_MUTED,
                    "align": "center",
                    "size": "xs",
                }

            row_contents = [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "⚔️", "size": "sm", "flex": 0},
                        {
                            "type": "text",
                            "text": q.title,
                            "weight": "bold",
                            "color": COLOR_TEXT,
                            "flex": 1,
                            "wrap": True,
                            "margin": "sm",
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": f"難度 {q.difficulty_tier}",
                                    "size": "xxs",
                                    "weight": "bold",
                                    "color": COLOR_BADGE_TEXT,
                                    "align": "center",
                                }
                            ],
                            "backgroundColor": diff_color,
                            "cornerRadius": "8px",
                            "paddingAll": "xs",
                            "flex": 0,
                        },
                    ],
                    "alignItems": "center",
                },
                {
                    "type": "text",
                    "text": q.description or "尚未提供說明。",
                    "size": "xs",
                    "color": COLOR_MUTED,
                    "wrap": True,
                    "margin": "sm",
                },
            ]

            if verification_hint:
                row_contents.append(
                    {
                        "type": "text",
                        "text": f"驗證方式：{verification_hint}",
                        "size": "xxs",
                        "color": COLOR_MUTED,
                        "wrap": True,
                        "margin": "xs",
                    }
                )

            if loot_chance_text:
                row_contents.append(
                    {
                        "type": "text",
                        "text": loot_chance_text,
                        "size": "xxs",
                        "color": COLOR_REWARD,
                        "margin": "xs",
                    }
                )

            row_contents.append(
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"+{q.xp_reward} 經驗",
                            "color": COLOR_REWARD,
                            "size": "xs",
                            "flex": 1,
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [action_component],
                            "flex": 0,
                        },
                    ],
                    "margin": "md",
                    "alignItems": "center",
                }
            )

            row = {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": COLOR_CARD,
                "cornerRadius": "12px",
                "paddingAll": "md",
                "margin": "md",
                "contents": row_contents,
            }
            quest_rows.append(row)

        if not quest_rows and not habit_rows:
            quest_rows.append(
                {
                    "type": "text",
                    "text": "目前沒有任務，可重新生成。",
                    "color": COLOR_MUTED,
                    "align": "center",
                    "margin": "lg",
                }
            )

        habit_count = len(habits) if habits else 0
        quest_count = len(quests)

        body_contents = []
        if habit_rows:
            body_contents.append(
                {
                    "type": "text",
                    "text": f"例行模組｜{habit_count} / 2",
                    "weight": "bold",
                    "color": "#38BDF8",
                    "size": "xs",
                    "margin": "md",
                }
            )
            body_contents.extend(habit_rows)

        if quest_rows:
            body_contents.append(
                {
                    "type": "text",
                    "text": f"今日任務｜{quest_count} / 3",
                    "weight": "bold",
                    "color": COLOR_ACCENT,
                    "size": "xs",
                    "margin": "md",
                }
            )
            body_contents.extend(quest_rows)

        bubble = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "🕹️ 作戰面板｜任務清單",
                        "weight": "bold",
                        "color": COLOR_ACCENT,
                        "size": "sm",
                    },
                    {
                        "type": "text",
                        "text": "今日 3 任務 + 2 打卡",
                        "color": COLOR_MUTED,
                        "size": "xxs",
                        "margin": "xs",
                    },
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": body_contents,
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "postback",
                            "label": "♻️ 重新生成 (100G)",
                            "data": "action=reroll_quests",
                            "displayText": "重新生成任務 (消耗 100G)",
                        },
                        "style": "secondary",
                        "height": "sm",
                    }
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "md",
            },
        }

        return FlexMessage(alt_text="今日任務", contents=FlexContainer.from_dict(bubble))

    def render_profile(self, user) -> FlexMessage:
        COLOR_BG = "#0B0F14"
        COLOR_PANEL = "#111827"
        COLOR_ACCENT = "#7DF9FF"
        COLOR_TEXT = "#E6EDF3"
        COLOR_MUTED = "#8B949E"

        settings = user.settings or {"theme": "cyberpunk", "notifications": True}

        # Toggles
        is_notif_on = settings.get("notifications", True)
        notif_text = "開啟" if is_notif_on else "靜音"
        notif_color = "#20D6C7" if is_notif_on else "#FF5555"
        notif_val = "false" if is_notif_on else "true"

        theme_current = settings.get("theme", "cyberpunk")
        theme_next = "classic" if theme_current == "cyberpunk" else "cyberpunk"
        theme_text = "賽博龐克" if theme_current == "cyberpunk" else "經典簡約"

        bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "⚙️ 用戶設定", "weight": "bold", "color": COLOR_ACCENT, "size": "xl"},
                    {
                        "type": "text",
                        "text": f"{user.name} (Lv.{user.level})",
                        "color": COLOR_MUTED,
                        "size": "sm",
                        "margin": "xs",
                    },
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    # Stats Summary
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "📊 核心屬性",
                                "color": COLOR_TEXT,
                                "weight": "bold",
                                "size": "sm",
                            },
                            {
                                "type": "text",
                                "text": f"STR: {user.str} | INT: {user.int} | VIT: {user.vit}",
                                "color": COLOR_MUTED,
                                "size": "xs",
                                "margin": "sm",
                            },
                            {
                                "type": "text",
                                "text": f"WIS: {user.wis} | CHA: {user.cha}",
                                "color": COLOR_MUTED,
                                "size": "xs",
                            },
                        ],
                        "backgroundColor": COLOR_PANEL,
                        "paddingAll": "md",
                        "cornerRadius": "md",
                        "margin": "md",
                    },
                    # Settings Section
                    {
                        "type": "text",
                        "text": "偏好設定",
                        "color": COLOR_TEXT,
                        "weight": "bold",
                        "size": "sm",
                        "margin": "xl",
                    },
                    {"type": "separator", "margin": "md", "color": "#30363D"},
                    # Theme Row
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "介面風格",
                                "color": COLOR_TEXT,
                                "size": "sm",
                                "gravity": "center",
                                "flex": 1,
                            },
                            {
                                "type": "button",
                                "style": "secondary",
                                "height": "sm",
                                "action": {
                                    "type": "postback",
                                    "label": theme_text,
                                    "data": f"action=toggle_setting&key=theme&value={theme_next}",
                                    "displayText": f"切換風格至 {theme_next}",
                                },
                            },
                        ],
                        "margin": "md",
                        "alignItems": "center",
                    },
                    # Notif Row
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "推播通知",
                                "color": COLOR_TEXT,
                                "size": "sm",
                                "gravity": "center",
                                "flex": 1,
                            },
                            {
                                "type": "button",
                                "style": "primary",
                                "color": notif_color,
                                "height": "sm",
                                "action": {
                                    "type": "postback",
                                    "label": notif_text,
                                    "data": f"action=toggle_setting&key=notifications&value={notif_val}",
                                    "displayText": f"切換通知: {notif_val}",
                                },
                            },
                        ],
                        "margin": "md",
                        "alignItems": "center",
                    },
                    # Language (Static)
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "語言區域",
                                "color": COLOR_TEXT,
                                "size": "sm",
                                "gravity": "center",
                                "flex": 1,
                            },
                            {
                                "type": "text",
                                "text": "繁體中文 (TW)",
                                "color": COLOR_MUTED,
                                "size": "sm",
                                "align": "end",
                                "flex": 1,
                            },
                        ],
                        "margin": "md",
                        "alignItems": "center",
                    },
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
        }
        return FlexMessage(alt_text="用戶設定", contents=FlexContainer.from_dict(bubble))

    def render_help_card(self, help_data: dict) -> FlexMessage:
        COLOR_BG = "#0B0F14"
        COLOR_ACCENT = "#7DF9FF"
        COLOR_TEXT = "#E6EDF3"
        COLOR_MUTED = "#8B949E"

        # help_data: {title, message, suggestion, action_label, action_data}

        title = help_data.get("title", "💡 提示")
        message = help_data.get("message", "")
        suggestion = help_data.get("suggestion", "")
        action_label = help_data.get("action_label", "查看")
        action_data = help_data.get("action_data", "action=menu")

        bubble = {
            "type": "bubble",
            "size": "kilo",  # Smaller card
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [{"type": "text", "text": title, "weight": "bold", "color": COLOR_ACCENT, "size": "md"}],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": message, "color": COLOR_TEXT, "size": "sm", "wrap": True},
                    {
                        "type": "text",
                        "text": suggestion,
                        "color": COLOR_MUTED,
                        "size": "xs",
                        "wrap": True,
                        "margin": "md",
                    },
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {"type": "postback", "label": action_label, "data": action_data},
                        "style": "secondary",
                        "height": "sm",
                    }
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "md",
            },
        }
        return FlexMessage(alt_text="提示", contents=FlexContainer.from_dict(bubble))

    def render_push_briefing(
        self,
        title: str,
        quests: list,
        habits: list | None = None,
        hint: str | None = None,
    ) -> FlexMessage:
        COLOR_BG = "#0B0F14"
        COLOR_CARD = "#151C2B"
        COLOR_ACCENT = "#00F5FF"
        COLOR_TEXT = "#F8FAFC"
        COLOR_MUTED = "#94A3B8"
        COLOR_LINE = "#1F2937"

        quest_rows = []
        for q in quests[:3]:
            quest_rows.append(
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "⚔️", "size": "xs", "flex": 0},
                        {
                            "type": "text",
                            "text": q.title,
                            "size": "sm",
                            "color": COLOR_TEXT,
                            "wrap": True,
                            "flex": 1,
                            "margin": "sm",
                        },
                    ],
                    "margin": "sm",
                }
            )

        habit_rows = []
        if habits:
            for h in habits[:2]:
                label = getattr(h, "habit_name", None) or getattr(h, "habit_tag", None) or "習慣"
                habit_rows.append(
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "🔄", "size": "xs", "flex": 0},
                            {
                                "type": "text",
                                "text": label,
                                "size": "sm",
                                "color": COLOR_TEXT,
                                "wrap": True,
                                "flex": 1,
                                "margin": "sm",
                            },
                        ],
                        "margin": "sm",
                    }
                )

        if not quest_rows:
            quest_rows.append(
                {
                    "type": "text",
                    "text": "目前尚無任務。",
                    "color": COLOR_MUTED,
                    "size": "xs",
                }
            )

        body_contents = []
        if hint:
            body_contents.append(
                {
                    "type": "text",
                    "text": hint,
                    "size": "xs",
                    "color": COLOR_ACCENT,
                    "wrap": True,
                    "margin": "sm",
                }
            )

        body_contents.append(
            {
                "type": "text",
                "text": "任務摘要",
                "size": "xs",
                "color": COLOR_MUTED,
                "margin": "md",
            }
        )
        body_contents.extend(quest_rows)

        if habit_rows:
            body_contents.append({"type": "separator", "margin": "md", "color": COLOR_LINE})
            body_contents.append(
                {
                    "type": "text",
                    "text": "今日打卡",
                    "size": "xs",
                    "color": COLOR_MUTED,
                    "margin": "md",
                }
            )
            body_contents.extend(habit_rows)

        bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "weight": "bold",
                        "color": COLOR_ACCENT,
                        "size": "sm",
                    }
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": body_contents,
                "backgroundColor": COLOR_CARD,
                "paddingAll": "lg",
            },
        }

        return FlexMessage(alt_text=title, contents=FlexContainer.from_dict(bubble))

    def render_inventory(self, user: User, items: list) -> FlexMessage:
        COLOR_BG = "#0D1117"
        COLOR_ACCENT = "#7DF9FF"

        if not items:
            return FlexMessage(
                alt_text="🎒 背包",
                contents=FlexContainer.from_dict(
                    {
                        "type": "bubble",
                        "size": "giga",
                        "body": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "🎒 背包",
                                    "weight": "bold",
                                    "color": COLOR_ACCENT,
                                    "size": "xl",
                                },
                                {
                                    "type": "text",
                                    "text": f"持有金幣: 💰 {user.gold or 0}",
                                    "size": "sm",
                                    "color": "#F5C542",
                                    "margin": "md",
                                },
                                {"type": "separator", "color": "#30363D", "margin": "md"},
                                {
                                    "type": "text",
                                    "text": "空空如也...",
                                    "color": "#8B949E",
                                    "size": "sm",
                                    "margin": "lg",
                                    "align": "center",
                                },
                            ],
                            "backgroundColor": COLOR_BG,
                            "paddingAll": "xl",
                        },
                    }
                ),
            )

        item_rows = []
        for item, qty in items:
            # Visual tweaks based on rarity
            rarity_color = "#8B949E"
            if item.rarity == "UNCOMMON":
                rarity_color = "#20D6C7"
            if item.rarity == "RARE":
                rarity_color = "#F5C542"
            if item.rarity == "EPIC":
                rarity_color = "#C77DFF"

            row = {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": item.name, "weight": "bold", "color": "#E6EDF3", "size": "sm"},
                            {
                                "type": "text",
                                "text": f"{item.rarity} | {item.type}",
                                "size": "xxs",
                                "color": rarity_color,
                            },
                        ],
                        "flex": 3,
                    },
                    {
                        "type": "text",
                        "text": f"x{qty}",
                        "weight": "bold",
                        "color": "#F5C542",
                        "align": "end",
                        "gravity": "center",
                        "flex": 1,
                    },
                ],
                "margin": "md",
                "action": {"type": "postback", "label": "Detail", "data": f"action=item_detail&id={item.id}"},
            }
            item_rows.append(row)
            item_rows.append({"type": "separator", "color": "#30363D", "margin": "sm"})

        bubble = {
            "type": "bubble",
            "size": "giga",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "🎒 戰術背包", "weight": "bold", "color": COLOR_ACCENT, "size": "xl"},
                    {
                        "type": "text",
                        "text": f"持有金幣: 💰 {user.gold or 0}",
                        "size": "xs",
                        "color": "#F5C542",
                        "margin": "sm",
                    },
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": item_rows,
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
        }
        return FlexMessage(alt_text="🎒 背包清單", contents=FlexContainer.from_dict(bubble))

    def render_shop_list(self, items: list, user_gold: int) -> FlexMessage:
        COLOR_BG = "#0D1117"
        COLOR_ACCENT = "#F5C542"

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
                            {
                                "type": "text",
                                "text": item.name,
                                "weight": "bold",
                                "color": "#E6EDF3",
                                "size": "sm",
                            },
                            {
                                "type": "text",
                                "text": f"{item.price} G",
                                "color": COLOR_ACCENT,
                                "size": "xs",
                            },
                        ],
                        "flex": 1,
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": "#238636",
                        "action": {
                            "type": "postback",
                            "label": "購買",
                            "data": f"action=buy_item&item_id={item.id}",
                            "displayText": f"購買 {item.name}",
                        },
                        "flex": 0,
                    },
                ],
                "margin": "md",
                "alignItems": "center",
            }
            item_rows.append(row)
            item_rows.append({"type": "separator", "margin": "md", "color": "#30363D"})

        if not item_rows:
            item_rows.append(
                {
                    "type": "text",
                    "text": "黑市目前沒有貨。",
                    "color": "#8B949E",
                    "align": "center",
                }
            )

        bubble = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "🛒 黑市交易所",
                        "weight": "bold",
                        "color": COLOR_ACCENT,
                        "size": "md",
                    },
                    {
                        "type": "text",
                        "text": f"餘額：{user_gold} G",
                        "color": "#E6EDF3",
                        "size": "xs",
                        "align": "end",
                    },
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": item_rows,
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
        }

        return FlexMessage(alt_text="黑市交易所", contents=FlexContainer.from_dict(bubble))

    def render_crafting_menu(self, recipes: list) -> FlexMessage:
        COLOR_BG = "#0D1117"
        COLOR_ACCENT = "#D2A8FF"

        recipe_rows = []
        for r_data in recipes:
            recipe = r_data["recipe"]
            can_craft = r_data["can_craft"]
            missing = r_data["missing"]

            if can_craft:
                action_btn = {
                    "type": "button",
                    "style": "primary",
                    "height": "sm",
                    "color": COLOR_ACCENT,
                    "action": {
                        "type": "postback",
                        "label": "合成",
                        "data": f"action=craft&recipe_id={recipe.id}",
                        "displayText": f"合成 {recipe.name}",
                    },
                    "flex": 0,
                }
                status_text = {
                    "type": "text",
                    "text": "✅ 可合成",
                    "size": "xxs",
                    "color": "#00FF9D",
                }
            else:
                action_btn = {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "未解鎖",
                        "data": "action=noop",
                    },
                    "flex": 0,
                }
                status_text = {
                    "type": "text",
                    "text": f"❌ 缺少：{', '.join(missing)}",
                    "size": "xxs",
                    "color": "#FF5555",
                    "wrap": True,
                }

            row = {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": recipe.name,
                                "weight": "bold",
                                "color": "#E6EDF3",
                                "size": "sm",
                                "flex": 1,
                            },
                            action_btn,
                        ],
                        "alignItems": "center",
                    },
                    status_text,
                    {"type": "separator", "margin": "sm", "color": "#30363D"},
                ],
                "margin": "md",
            }
            recipe_rows.append(row)

        bubble = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "🔧 鍊金實驗室", "weight": "bold", "color": COLOR_ACCENT, "size": "md"}
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": recipe_rows,
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
        }
        return FlexMessage(alt_text="合成實驗室", contents=FlexContainer.from_dict(bubble))

    def render_boss_encounter(self, user, boss) -> FlexMessage:
        COLOR_BG = "#161B22"
        COLOR_BOSS = "#DA3633"  # Red

        if not boss:
            # Render "Summon" View
            bubble = {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "沒有活躍的首領",
                            "color": "#8B949E",
                            "align": "center",
                            "weight": "bold",
                        },
                        {
                            "type": "text",
                            "text": "召喚心中的惡魔來對抗吧...",
                            "color": "#8B949E",
                            "size": "xs",
                            "align": "center",
                            "margin": "sm",
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "color": COLOR_BOSS,
                            "action": {
                                "type": "postback",
                                "label": "召喚首領",
                                "data": "action=spawn_boss",
                                "displayText": "召喚首領",
                            },
                            "margin": "lg",
                        },
                    ],
                    "backgroundColor": COLOR_BG,
                    "paddingAll": "xl",
                },
            }
            return FlexMessage(alt_text="首領召喚", contents=FlexContainer.from_dict(bubble))

        # Render "Combat" View
        hp_percent = int((boss.hp / boss.max_hp) * 100)

        # HP Bar Logic (Simulated with Box width? iterating separators? Line Flex doesn't do percent width easily)
        # Using a text representation for simplicity first: "HP: [|||||     ] 50%"
        hp_text = f"HP: {boss.hp}/{boss.max_hp}"

        bubble = {
            "type": "bubble",
            "size": "giga",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"👹 {boss.name} (Lv.{boss.level})",
                        "weight": "bold",
                        "color": COLOR_BOSS,
                        "size": "xl",
                    },
                    {"type": "text", "text": hp_text, "color": "#F0883E", "weight": "bold", "margin": "sm"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [],
                        "backgroundColor": "#30363D",
                        "height": "6px",
                        "margin": "sm",
                        "cornerRadius": "3px",
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [],
                        "backgroundColor": "#F0883E",
                        "height": "6px",
                        "width": f"{hp_percent}%",
                        "position": "absolute",
                        "offsetTop": "53px",  # Adjust based on header height... tricky. simplified: use separate box
                        "offsetStart": "20px",
                        "cornerRadius": "3px",
                    },
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "首領正在注視著你...",
                        "color": "#8B949E",
                        "size": "sm",
                        "align": "center",
                        "margin": "md",
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": COLOR_BOSS,
                        "action": {
                            "type": "postback",
                            "label": "⚔️ 攻擊 (消耗 50 XP)",
                            "data": "action=attack_boss",
                            "displayText": "攻擊首領",
                        },
                        "margin": "xl",
                        "height": "sm",
                    },
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
        }
        # Re-adjust HP bar visual: Line Flex absolute positioning is hard to guess.
        # Easier: progress bar using linear-gradient background? Not supported.
        # Simple method: 2 boxes horizontal, weighted flex.

        hp_bar_container = {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#F0883E",
                    "flex": hp_percent if hp_percent > 0 else 0,
                    "height": "6px",
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#30363D",
                    "flex": 100 - hp_percent,
                    "height": "6px",
                },
            ],
            "margin": "sm",
            "cornerRadius": "3px",
            "backgroundColor": "#30363D",
        }

        # Inject HP bar into header contents correctly
        bubble["header"]["contents"] = [
            {
                "type": "text",
                "text": f"👹 {boss.name} (Lv.{boss.level})",
                "weight": "bold",
                "color": COLOR_BOSS,
                "size": "xl",
            },
            {"type": "text", "text": hp_text, "color": "#F0883E", "weight": "bold", "margin": "sm"},
            hp_bar_container,
        ]

        return FlexMessage(alt_text=f"首領戰: {boss.name}", contents=FlexContainer.from_dict(bubble))

    def render_boss_status(self, boss) -> FlexMessage:
        if not boss:
            return TextMessage(text="目前沒有首領，輸入「Boss」即可召喚。")

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
                    {
                        "type": "text",
                        "text": "☠️ 首領戰",
                        "weight": "bold",
                        "color": "#FF5555",
                        "size": "sm",
                    },
                    {
                        "type": "text",
                        "text": boss.name,
                        "weight": "bold",
                        "color": "#FFFFFF",
                        "size": "xl",
                        "margin": "sm",
                    },
                    {
                        "type": "text",
                        "text": f"等級 {boss.level}",
                        "color": "#8B949E",
                        "size": "xs",
                    },
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
                                "cornerRadius": "md",
                                "contents": [],
                            }
                        ],
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"生命值 {boss.hp}/{boss.max_hp}",
                                "size": "xs",
                                "color": "#E6EDF3",
                            },
                            {
                                "type": "text",
                                "text": f"{percentage}%",
                                "size": "xs",
                                "color": "#E6EDF3",
                                "align": "end",
                            },
                        ],
                        "margin": "sm",
                    },
                    {"type": "separator", "margin": "md", "color": "#30363D"},
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
                                    "label": "⚔️ 攻擊",
                                    "text": "攻擊",
                                },
                            }
                        ],
                    },
                ],
            },
        }

        return FlexMessage(alt_text=f"首領戰：{boss.name}", contents=FlexContainer.from_dict(bubble))

    def render_plan_confirmation(self, goal_title: str, milestones: list, habits: list) -> FlexMessage:
        COLOR_BG = "#0D1117"
        COLOR_ACCENT = "#2f81f7"

        m_rows = []
        for m in milestones:
            m_rows.append(
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "🔹", "flex": 0, "size": "xxs"},
                        {
                            "type": "text",
                            "text": f"{m.get('title')}（{m.get('difficulty', 'C')}）",
                            "color": "#E6EDF3",
                            "size": "xs",
                            "flex": 1,
                            "wrap": True,
                            "margin": "sm",
                        },
                    ],
                    "margin": "sm",
                }
            )

        h_rows = []
        for h in habits:
            h_rows.append(
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "🔄", "flex": 0, "size": "xxs"},
                        {
                            "type": "text",
                            "text": h.get("title", "新習慣"),
                            "color": "#7DF9FF",
                            "size": "xs",
                            "flex": 1,
                            "wrap": True,
                            "margin": "sm",
                        },
                    ],
                    "margin": "sm",
                }
            )

        body_contents = [
            {
                "type": "text",
                "text": "🎯 戰術規劃完成",
                "weight": "bold",
                "color": COLOR_ACCENT,
                "size": "sm",
            },
            {
                "type": "text",
                "text": goal_title,
                "weight": "bold",
                "color": "#E6EDF3",
                "size": "lg",
                "margin": "sm",
                "wrap": True,
            },
            {"type": "separator", "margin": "md", "color": "#30363D"},
            {
                "type": "text",
                "text": "里程碑",
                "weight": "bold",
                "color": "#8B949E",
                "size": "xxs",
                "margin": "lg",
            },
            {
                "type": "box",
                "layout": "vertical",
                "contents": m_rows or [{"type": "text", "text": "尚無", "size": "xs", "color": "#8B949E"}],
            },
            {
                "type": "text",
                "text": "新習慣",
                "weight": "bold",
                "color": "#8B949E",
                "size": "xxs",
                "margin": "lg",
            },
            {
                "type": "box",
                "layout": "vertical",
                "contents": h_rows or [{"type": "text", "text": "尚無", "size": "xs", "color": "#8B949E"}],
            },
        ]

        return FlexMessage(
            alt_text="計畫確認",
            contents=FlexContainer.from_dict(
                {
                    "type": "bubble",
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": body_contents,
                        "backgroundColor": COLOR_BG,
                        "paddingAll": "lg",
                    },
                    "footer": {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "button",
                                "action": {
                                    "type": "message",
                                    "label": "✅ 接受計畫",
                                    "text": "狀態",
                                },
                                "style": "primary",
                                "color": "#238636",
                            }
                        ],
                        "backgroundColor": COLOR_BG,
                        "paddingAll": "md",
                    },
                }
            ),
        )

    def render_goal_card(self, title: str, category: str = "general") -> FlexMessage:
        """Renders a 'Goal Contract' card when AI creates a new goal."""
        COLOR_BG = "#0D1117"
        COLOR_ACCENT = "#7DF9FF"
        COLOR_TEXT = "#E6EDF3"
        COLOR_MUTED = "#8B949E"

        category_emoji = {
            "health": "💪",
            "career": "💼",
            "learning": "📚",
            "finance": "💰",
            "social": "🤝",
        }.get(category.lower(), "🎯")

        bubble = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": "📜 目標契約",
                        "weight": "bold",
                        "color": COLOR_ACCENT,
                        "size": "sm",
                    },
                    {
                        "type": "text",
                        "text": f"{category_emoji} {category.upper()}",
                        "color": COLOR_MUTED,
                        "size": "xxs",
                        "align": "end",
                    },
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "weight": "bold",
                        "color": COLOR_TEXT,
                        "size": "lg",
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": "契約已簽署。系統將自動分解為可執行任務。",
                        "color": COLOR_MUTED,
                        "size": "xs",
                        "margin": "md",
                        "wrap": True,
                    },
                ],
                "backgroundColor": "#161B22",
                "paddingAll": "lg",
            },
        }

        return FlexMessage(alt_text=f"目標契約：{title}", contents=FlexContainer.from_dict(bubble))

    def render_quest_brief(self, title: str, difficulty: str = "C", xp_reward: int = 50) -> FlexMessage:
        """Renders a 'Mission Brief' card when AI starts a challenge/quest."""
        COLOR_BG = "#0D1117"
        COLOR_ACCENT = "#00F5FF"
        COLOR_TEXT = "#E6EDF3"

        tier_colors = {
            "S": "#FF3B6B",
            "A": "#FF6B6B",
            "B": "#FFB020",
            "C": "#F6D365",
            "D": "#5CDE7A",
            "E": "#20D6C7",
        }
        diff_color = tier_colors.get(difficulty.upper(), COLOR_ACCENT)

        bubble = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": "⚔️ 任務啟動",
                        "weight": "bold",
                        "color": COLOR_ACCENT,
                        "size": "sm",
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"難度 {difficulty.upper()}",
                                "size": "xxs",
                                "weight": "bold",
                                "color": "#0B0F14",
                                "align": "center",
                            }
                        ],
                        "backgroundColor": diff_color,
                        "paddingAll": "xs",
                        "cornerRadius": "8px",
                    },
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "weight": "bold",
                        "color": COLOR_TEXT,
                        "size": "lg",
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": f"+{xp_reward} 經驗值",
                        "color": "#FACC15",
                        "size": "sm",
                        "margin": "md",
                    },
                ],
                "backgroundColor": "#161B22",
                "paddingAll": "lg",
            },
        }

        return FlexMessage(alt_text=f"任務啟動：{title}", contents=FlexContainer.from_dict(bubble))

    def render_rival_card(
        self, rival_name: str, rival_level: int, rival_xp: int, user_level: int, taunt: str = ""
    ) -> FlexMessage:
        """Renders a 'Rival Dossier' card showing enemy stats."""
        COLOR_BG = "#0D1117"
        COLOR_DANGER = "#FF3B6B"
        COLOR_TEXT = "#E6EDF3"
        COLOR_MUTED = "#8B949E"

        # Threat level calculation
        level_diff = rival_level - user_level
        if level_diff >= 3:
            threat_text = "☠️ 極度危險"
            threat_color = "#FF3B6B"
        elif level_diff >= 1:
            threat_text = "⚠️ 威脅中"
            threat_color = "#FFB020"
        elif level_diff >= -1:
            threat_text = "⚔️ 勢均力敵"
            threat_color = "#7DF9FF"
        else:
            threat_text = "✓ 優勢"
            threat_color = "#5CDE7A"

        bubble = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": "🐍 敵人檔案",
                        "weight": "bold",
                        "color": COLOR_DANGER,
                        "size": "sm",
                    },
                    {
                        "type": "text",
                        "text": threat_text,
                        "color": threat_color,
                        "size": "xxs",
                        "align": "end",
                    },
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": rival_name,
                        "weight": "bold",
                        "color": COLOR_TEXT,
                        "size": "xl",
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": f"Lv.{rival_level}", "color": COLOR_DANGER, "size": "lg"},
                            {
                                "type": "text",
                                "text": f"XP: {rival_xp}",
                                "color": COLOR_MUTED,
                                "size": "sm",
                                "align": "end",
                            },
                        ],
                        "margin": "sm",
                    },
                    {"type": "separator", "margin": "md", "color": "#30363D"},
                    {
                        "type": "text",
                        "text": f"「{taunt}」" if taunt else "「沉默...」",
                        "color": COLOR_MUTED,
                        "size": "sm",
                        "margin": "md",
                        "wrap": True,
                        "style": "italic",
                    },
                ],
                "backgroundColor": "#161B22",
                "paddingAll": "lg",
            },
        }

        return FlexMessage(alt_text=f"敵人: {rival_name}", contents=FlexContainer.from_dict(bubble))

    def render_hollowed_state(self, user_hp: int, max_hp: int = 100) -> FlexMessage:
        """Renders an 'Emergency Protocol' card when user is Hollowed (HP <= 0)."""
        COLOR_BG = "#1A0505"
        COLOR_DANGER = "#FF3B6B"
        COLOR_TEXT = "#FF6B6B"
        COLOR_MUTED = "#8B4545"

        hp_pct = max(0, int((user_hp / max_hp) * 100))

        bubble = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "⚠️ SYSTEM CRITICAL ⚠️",
                        "weight": "bold",
                        "color": COLOR_DANGER,
                        "size": "lg",
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": f"HP: {hp_pct}%",
                        "color": COLOR_MUTED,
                        "size": "xs",
                        "align": "center",
                        "margin": "sm",
                    },
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "lg",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "HOLLOWED PROTOCOL ACTIVE",
                        "weight": "bold",
                        "color": COLOR_TEXT,
                        "size": "md",
                        "align": "center",
                    },
                    {"type": "separator", "margin": "md", "color": "#4A1515"},
                    {
                        "type": "text",
                        "text": "所有任務已暫停。\n完成「救援地城」以恢復HP。",
                        "color": COLOR_MUTED,
                        "size": "sm",
                        "margin": "lg",
                        "wrap": True,
                        "align": "center",
                    },
                ],
                "backgroundColor": "#0F0505",
                "paddingAll": "xl",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {"type": "postback", "label": "🚨 進入救援", "data": "action=start_rescue"},
                        "style": "primary",
                        "color": COLOR_DANGER,
                    }
                ],
                "backgroundColor": COLOR_BG,
                "paddingAll": "md",
            },
        }

        return FlexMessage(alt_text="⚠️ HOLLOWED PROTOCOL", contents=FlexContainer.from_dict(bubble))


flex_renderer = FlexRenderer()
