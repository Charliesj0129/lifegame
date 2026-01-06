from app.services.tool_registry import tool_registry
from app.services.flex_renderer import flex_renderer
from app.services.shop_service import shop_service
from app.services.crafting_service import crafting_service
from app.services.boss_service import boss_service
from app.services.lore_service import lore_service
from app.services.quest_service import quest_service
from app.services.user_service import user_service
from linebot.v3.messaging import TextMessage, QuickReply, QuickReplyItem, PostbackAction as LinePostbackAction

# --- Handler Functions (Return: response_message, intent_tool_name) ---

async def handle_status(session, user_id: str, text: str):
    user = await user_service.get_or_create_user(session, user_id)
    lore_prog = await lore_service.get_user_progress(session, user_id)
    msg = flex_renderer.render_status(user, lore_prog)
    return msg, "get_status", {}

async def handle_quests(session, user_id: str, text: str):
    quests = await quest_service.get_daily_quests(session, user_id)
    habits = await quest_service.get_daily_habits(session, user_id)
    msg = flex_renderer.render_quest_list(quests, habits)
    return msg, "get_quests", {}

async def handle_inventory(session, user_id: str, text: str):
    _data, msg = await tool_registry.get_inventory(session, user_id)
    return msg, "get_inventory", {}

async def handle_shop(session, user_id: str, text: str):
    user = await user_service.get_or_create_user(session, user_id)
    items = await shop_service.list_shop_items(session)
    msg = flex_renderer.render_shop_list(items, user.gold or 0)
    return msg, "shop", {}

async def handle_craft(session, user_id: str, text: str):
    recipes = await crafting_service.get_available_recipes(session, user_id)
    msg = flex_renderer.render_crafting_menu(recipes)
    return msg, "craft", {}

async def handle_boss(session, user_id: str, text: str):
    boss = await boss_service.get_active_boss(session, user_id)
    if not boss:
        await boss_service.spawn_boss(session, user_id)
        boss = await boss_service.get_active_boss(session, user_id)
    msg = flex_renderer.render_boss_status(boss)
    return msg, "boss", {}

async def handle_dungeon(session, user_id: str, text: str):
    from app.services.dungeon_service import dungeon_service
    dungeon_type = "FOCUS"
    lowered = text.lower()
    if "寫作" in text or "writing" in lowered:
        dungeon_type = "WRITING"
    elif "程式" in text or "coding" in lowered:
        dungeon_type = "CODING"
    elif "冥想" in text or "靜心" in text or "meditation" in lowered:
        dungeon_type = "MEDITATION"

    dungeon, message = await dungeon_service.open_dungeon(session, user_id, dungeon_type)
    quick_reply = QuickReply(
        items=[
            QuickReplyItem(
                action=LinePostbackAction(label="✅ 完成階段", data="action=complete_dungeon_stage", display_text="完成副本階段")
            ),
            QuickReplyItem(
                action=LinePostbackAction(label="⏹️ 放棄副本", data="action=abandon_dungeon", display_text="放棄副本")
            ),
        ]
    )
    msg = TextMessage(text=message, quick_reply=quick_reply)
    return msg, "dungeon", {"success": dungeon is not None}

async def handle_attack(session, user_id: str, text: str):
    challenge = await boss_service.generate_attack_challenge()
    msg = TextMessage(
        text=f"⚔️ 首領挑戰：{challenge}",
        quick_reply=QuickReply(items=[
            QuickReplyItem(
                action=LinePostbackAction(label="完成", data="action=strike_boss&dmg=50", display_text="完成挑戰")
            )
        ])
    )
    return msg, "attack", {}

async def handle_help(session, user_id: str, text: str):
    msg = TextMessage(
        text=(
            "🧭 快捷功能\n"
            "狀態｜任務｜背包｜商店｜合成｜首領｜攻擊｜簽到\n"
            "任務操作：重新生成｜全部接受｜略過 Viper"
        )
    )
    return msg, "help", {}

async def ai_fallback(session, user_id: str, text: str):
    """Deep Integration with AI Service Router."""
    from app.services.verification_service import verification_service, Verdict
    from app.services.ai_service import ai_router

    # 1. Verification Logic Check (Reserved Words Excluded)
    # Actually, verification logic is complex. 
    # Let's delegate to verification_service IF it looks like a verification attempt?
    # Or just let AI decide.
    # Current webhook logic: 
    # if not reserved:
    #    match = auto_match_quest()
    #    if match: verify()
    #    else: ai_router()
    
    # We can try verification first
    quest_match = await verification_service.auto_match_quest(session, user_id, text, "TEXT")
    
    if quest_match:
        verdict, reason, follow_up = await verification_service.verify_text(session, quest_match, text)
        if verdict == Verdict.APPROVED:
            completion = await verification_service._complete_quest(session, user_id, quest_match)
            if completion.get("success") is False:
                return TextMessage(text=completion.get("message", "⚠️ 任務已完成或不存在。")), "verify_text", {"leveled_up": False}
            base_msg = (
                f"{completion.get('message', '✅ 任務完成！')}\n"
                f"獲得：{completion.get('xp', 0)} XP / {completion.get('gold', 0)} Gold"
            )
            if completion.get("story"):
                base_msg = f"{base_msg}\n\n_{completion['story']}_"
            return TextMessage(text=f"{base_msg}\n判定：{reason}"), "verify_text", {"leveled_up": False}
        elif verdict == Verdict.REJECTED:
             return TextMessage(text=f"未通過驗證：{reason}"), "verify_text", {}
        else:
             return TextMessage(text=follow_up or reason), "verify_text", {}

    # 2. AI Router
    router_result = await ai_router.router(session, user_id, text)
    if isinstance(router_result, tuple):
        if len(router_result) == 3:
            return router_result[0], router_result[1], router_result[2]
        elif len(router_result) == 2:
            return router_result[0], router_result[1], {}
            
    
    # Fallback
    if not router_result:
         return TextMessage(text="⚠️ 系統忙碌中。"), "error", {}
         
    return router_result, "ai_router", {}

def setup_dispatcher():
    from app.core.dispatcher import dispatcher
    
    # helper for precise matching
    def is_exact(target: str):
        return lambda text: text.strip().lower() == target or text.strip() == target
        
    def is_any(targets: list[str]):
        return lambda text: any(t in text.lower() for t in targets) or any(t in text for t in targets)

    # 1. Exact Matches (High Priority)
    dispatcher.register(lambda t: t.lower() in ["status", "狀態"], handle_status)
    dispatcher.register(lambda t: t.lower() in ["quests", "quest", "任務", "任務清單", "今日任務", "簽到", "打卡"], handle_quests)
    dispatcher.register(lambda t: t.lower() in ["inventory", "背包", "背包清單"], handle_inventory)
    
    # 2. Keyword Matches (Shop, Craft, Boss)
    # Shop: "shop", "store", "market", "商店", "黑市"
    dispatcher.register(is_any(["shop", "store", "market", "商店", "黑市", "市場"]), handle_shop)
    
    # Craft: "craft", "workshop", "合成", "工坊"
    dispatcher.register(is_any(["craft", "workshop", "合成", "工坊"]), handle_craft)
    
    # Boss: "boss", "首領", "魔王"
    dispatcher.register(is_any(["boss", "首領", "魔王"]), handle_boss)

    # Dungeon: "副本", "地城", "地下城"
    dispatcher.register(is_any(["副本", "地城", "地下城", "dungeon"]), handle_dungeon)
    
    # Attack: "attack", "攻擊"
    dispatcher.register(is_any(["attack", "攻擊"]), handle_attack)
    
    # Help: "help", "指令", "幫助"
    dispatcher.register(is_any(["help", "指令", "幫助", "說明", "功能"]), handle_help)

    # 3. Default AI
    dispatcher.register_default(ai_fallback)
