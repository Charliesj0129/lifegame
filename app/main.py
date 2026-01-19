from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.core.config import settings
from app.core.migrations import run_migrations
from app.core.logging_middleware import LoggingMiddleware

import asyncio
import inspect
import logging
import os

# Setup logging
from app.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# --- Core Imports (Explicit Dependencies) ---
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.core.dispatcher import dispatcher

# Domain & Adapters
# Domain & Adapters
from domain.models.game_result import GameResult
# from adapters.persistence.kuzu.adapter import get_kuzu_adapter # Use container

# Services (Lifted from Lazy Imports)
from application.services.game_loop import game_loop

# from application.services.brain_service import brain_service # Use container
# from application.services.user_service import user_service # Use container
from app.core.container import container
from application.services.hp_service import hp_service
from application.services.quest_service import quest_service
from application.services.lore_service import lore_service
from application.services.inventory_service import inventory_service
from application.services.shop_service import shop_service
from application.services.crafting_service import crafting_service
from application.services.boss_service import boss_service
from application.services.flex_renderer import flex_renderer

# Line Bot
from linebot.v3.messaging import QuickReply, QuickReplyItem, MessageAction


# --- Resilience: Global Exception Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Database Migration
    if settings.AUTO_MIGRATE:
        try:
            logging.info("AUTO_MIGRATE enabled; running migrations.")

            # Critical: Ensure data directory exists for Ephemeral DB
            os.makedirs("./data", exist_ok=True)

            # Critical: For Ephemeral SQLite/Kuzu, force clean slate to avoid Lock/Schema errors
            # 1. Clean SQLite
            if "sqlite" in str(settings.DATABASE_URL) or "sqlite" in str(settings.POSTGRES_SERVER):
                # Simple heuristic for sqlite path in connection string
                pass
                # (Skipping destructive wipe logic for now to preserve dev data safely, relying on alembic)
                # If explicit wipe needed, user requests it specifically.

            await asyncio.to_thread(run_migrations)

            # Seed Data (Shop Items)
            from app.core.seeding import seed_shop_items

            async with AsyncSessionLocal() as session:
                await seed_shop_items(session)

        except Exception:
            logging.exception("Auto migration failed.")
            # Don't raise, try to start anyway to allow /health
            pass

    # KuzuDB Initialization (Async & Lazy)
    if settings.KUZU_DATABASE_PATH:
        try:
            # DI: Use Container
            await container.kuzu_adapter.initialize()
            logging.info("KuzuDB Async Adapter Initialized.")
        except Exception as e:
            logging.error(f"KuzuDB Init Failed: {e}")

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    from fastapi.responses import JSONResponse
    from app.core.context import get_request_id

    req_id = get_request_id()
    logger.error(f"Global Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "request_id": req_id},
    )


# 1. Define Independent Handlers
async def handle_attack(session, user_id: str, text: str) -> GameResult:
    """Handle attack command"""
    return GameResult(text="⚔️ 你發動了攻擊！造成了 10 點傷害。", intent="attack")


async def handle_defend(session, user_id: str, text: str) -> GameResult:
    """Handle defend command"""
    return GameResult(text="🛡️ 你擺出了防禦姿態，傷害減少 50%。", intent="defend")


async def handle_ai_analysis(session, user_id: str, text: str) -> GameResult:
    """Handle natural language via BrainService (The Cortex) - Cognitive Upgrade."""
    # Fast-path: if the text matches a known command, short-circuit to local handler to avoid LLM call
    normalized = text.strip()
    quick_routes = {
        ("狀態", "status"): handle_status,
        ("任務", "quests"): handle_quests,
        ("簽到", "checkin"): handle_checkin,
        ("背包", "inventory"): handle_inventory,
        ("商店", "shop"): handle_shop,
        ("新目標",): handle_new_goal,
    }
    for keys, handler in quick_routes.items():
        if normalized in keys:
            return await handler(session, user_id, text)

    # --- PHASE 4: THE PULSE (LAZY EVALUATION) ---
    # DI: Usage
    user = await container.user_service.get_or_create_user(session, user_id)

    # 1. HP Drain
    try:
        drain_amount = await hp_service.calculate_daily_drain(session, user)
    except Exception:
        drain_amount = 0

    # 2. Viper/Quest Push
    pushed_quests = quest_service.trigger_push_quests(session, user_id)
    if inspect.isawaitable(pushed_quests):
        pushed_quests = await pushed_quests
    else:
        pushed_quests = pushed_quests or []

    pulsed_events = {
        "drain_amount": drain_amount,
        "viper_taunt": f"System rebooted. {len(pushed_quests)} tasks pending." if pushed_quests else None,
    }

    # --- PHASE 5: BRAIN TRANSPLANT ---
    if not settings.OPENROUTER_API_KEY and not settings.GOOGLE_API_KEY:
        return GameResult(text="⚠️ 未知指令，請重試或查看指令清單。", intent="ai_response")

    # Use Cortex (DI)
    plan = await container.brain_service.think_with_session(session, user_id, text, pulsed_events=pulsed_events)

    # Execute Plan
    if plan.stat_update:
        update_data = plan.stat_update
        if update_data.stat_type:
            stat_key = update_data.stat_type.lower()
            if hasattr(user, stat_key):
                curr = getattr(user, stat_key) or 0
                setattr(user, stat_key, curr + 1)

        if update_data.hp_change != 0:
            try:
                await hp_service.apply_hp_change(session, user, update_data.hp_change, source="brain_reward")
            except Exception:
                logger.warning("Skipped hp_change due to invalid user state")

        if update_data.gold_change != 0:
            user.gold = (user.gold or 0) + update_data.gold_change

        if update_data.xp_amount > 0:
            user.xp = (user.xp or 0) + update_data.xp_amount

        await session.commit()

    # Record Event to Graph (DI)
    await container.kuzu_adapter.record_user_event(
        user_id,
        "ACTION",
        {
            "content": plan.narrative,
            "stat_type": plan.stat_update.stat_type if plan.stat_update else "none",
            "raw_text": text,
            "flow_tone": plan.flow_state.get("tone", "neutral"),
        },
    )

    # Exec Tool Calls
    logger.info(f"AI Tool Calls Count: {len(plan.tool_calls)}")
    tool_flex_messages = []
    tool_calls = plan.tool_calls if isinstance(plan.tool_calls, list) else []

    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue
        try:
            tool_name = tool_call.get("tool")
            args = tool_call.get("args", {})
            logger.info(f"Executing AI Tool: {tool_name} with {args}")

            if tool_name == "create_goal":
                title = args.get("title", "New Goal")
                category = args.get("category", "general")
                _goal, _ai_plan = await quest_service.create_new_goal(session, user_id, goal_text=title)
                flex_msg = flex_renderer.render_goal_card(title=title, category=category)
                tool_flex_messages.append(flex_msg)
                await container.kuzu_adapter.record_user_event(
                    user_id, "AI_TOOL_CALL", {"tool": "create_goal", "title": title}
                )

            elif tool_name == "start_challenge":
                title = args.get("title", "Challenge")
                difficulty = args.get("difficulty", "E")
                quest = await quest_service.create_quest(
                    session, user_id, title=title, description="AI Challenge", difficulty=difficulty
                )
                xp = getattr(quest, "xp_reward", 50)
                flex_msg = flex_renderer.render_quest_brief(title=title, difficulty=difficulty, xp_reward=xp)
                tool_flex_messages.append(flex_msg)
                await container.kuzu_adapter.record_user_event(
                    user_id, "AI_TOOL_CALL", {"tool": "start_challenge", "title": title}
                )

        except Exception as e:
            logger.error(f"Tool Execution Failed ({tool_name}): {e}", exc_info=True)
            plan.narrative += f"\n[SYSTEM ERROR: {tool_name}]"

    result_meta = {"plan": plan.model_dump()}
    if tool_flex_messages:
        result_meta["flex_messages"] = tool_flex_messages

    # Quick Reply
    quick_reply = QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label="📊 狀態", text="狀態")),
            QuickReplyItem(action=MessageAction(label="📋 任務", text="任務")),
            QuickReplyItem(action=MessageAction(label="🎯 新目標", text="我想設定新目標")),
        ]
    )
    result_meta["quick_reply"] = quick_reply

    narrative_text = plan.narrative or ""
    keywords = ["無法處理", "未知", "戰略", "警告", "偵測", "無效"]
    if not any(k in narrative_text for k in keywords):
        narrative_text = f"⚠️ 警告：{narrative_text}" if narrative_text else "⚠️ 警告：未知指令"

    return GameResult(text=narrative_text, intent="ai_response", metadata=result_meta)


# =============================================================================
# Phase 3: Chinese Command Handlers (Fixes 1-4)
# =============================================================================


async def handle_status(session: AsyncSession, user_id: str, text: str) -> GameResult:
    """Handler for '狀態' command - returns user status Flex card."""
    # Ultra-defensive: Multiple fallback levels
    user = None
    try:
        user = await container.user_service.get_or_create_user(session, user_id)
    except Exception as e:
        logger.error(f"Status: Failed to get user: {e}", exc_info=True)
        return GameResult(text=f"⚠️ 無法載入使用者資料: {str(e)[:50]}", intent="status_error")

    # Fallback Level 1: Try to render full Flex card
    try:
        lore_prog = []
        try:
            lore_prog = await lore_service.get_user_progress(session, user_id)
        except Exception:
            pass  # Ignore lore errors, proceed with empty list

        flex = flex_renderer.render_status(user, lore_prog)
        return GameResult(text="📊 玩家狀態", intent="status", metadata={"flex_message": flex})
    except Exception as render_err:
        logger.error(f"Render status failed: {render_err}", exc_info=True)

    # Fallback Level 2: Plain text status
    try:
        name = getattr(user, "name", None) or "玩家"
        level = getattr(user, "level", 1) or 1
        hp = getattr(user, "hp", 100) or 100
        max_hp = getattr(user, "max_hp", 100) or 100
        gold = getattr(user, "gold", 0) or 0
        job = getattr(user, "job_class", "冒險者") or "冒險者"

        plain_text = f"📊 **玩家狀態**\n👤 {name} | Lv.{level} {job}\n❤️ HP: {hp}/{max_hp}\n💰 金幣: {gold}"
        return GameResult(text=plain_text, intent="status_text_fallback")
    except Exception as e:
        logger.error(f"Status text fallback failed: {e}", exc_info=True)
        return GameResult(text=f"⚠️ 狀態載入失敗: {str(e)[:50]}", intent="status_critical_error")


async def handle_quests(session: AsyncSession, user_id: str, text: str) -> GameResult:
    """Handler for '任務' command - returns quest list Flex card."""
    quests = await quest_service.get_daily_quests(session, user_id)
    if quests:
        flex = flex_renderer.render_quest_list(quests)
        return GameResult(text="📋 今日任務", intent="quests", metadata={"flex_message": flex})
    else:
        return GameResult(text="📭 目前沒有任務。試試說「我想...」來設定新目標！", intent="quests")


async def handle_new_goal(session: AsyncSession, user_id: str, text: str) -> GameResult:
    """Handler for '新目標' or goal-setting intent."""
    goal_text = text.replace("新目標", "").replace("我想設定", "").replace("我想", "").strip()

    if len(goal_text) > 3:
        goal, ai_plan = await quest_service.create_new_goal(session, user_id, goal_text=goal_text)
        flex = flex_renderer.render_goal_card(title=goal_text, category="general")
        return GameResult(
            text=f"🎯 目標「{goal_text}」已建立！",
            intent="goal_created",
            metadata={"flex_message": flex},
        )
    else:
        return GameResult(text="🎯 你想達成什麼目標？（例如：學Python、減肥、早起）", intent="goal_prompt")


async def handle_checkin(session: AsyncSession, user_id: str, text: str) -> GameResult:
    """Handler for '簽到' command."""
    try:
        user = await container.user_service.get_or_create_user(session, user_id)
        user.gold = (user.gold or 0) + 10
        user.xp = (user.xp or 0) + 5
        await session.commit()

        # Record to Graph
        await container.kuzu_adapter.record_user_event(user_id, "CHECKIN", {"gold": 10, "xp": 5})

        return GameResult(
            text="✅ 簽到成功！+10 金幣 +5 經驗值",
            intent="checkin",
            metadata={"gold_gained": 10, "xp_gained": 5},
        )
    except Exception as e:
        logger.error(f"Checkin failed: {e}", exc_info=True)
        return GameResult(text="⚠️ 簽到失敗，請稍後再試。", intent="checkin_error")


async def handle_inventory(session: AsyncSession, user_id: str, text: str) -> GameResult:
    """Handler for '背包' command."""
    try:
        user = await container.user_service.get_or_create_user(session, user_id)
        await inventory_service.seed_default_items_if_needed(session)
        items = await inventory_service.get_inventory(session, user_id)
        flex = flex_renderer.render_inventory(user, items)
        return GameResult(text=f"🎒 背包：{len(items)} 件物品", intent="inventory", metadata={"flex_message": flex})
    except Exception as e:
        logger.error(f"Inventory failed: {e}", exc_info=True)
        return GameResult(text="⚠️ 背包載入失敗。", intent="inventory_error")


async def handle_shop(session: AsyncSession, user_id: str, text: str) -> GameResult:
    """Handler for '商店' command."""
    try:
        items = await shop_service.get_daily_stock(session)
        if items:
            flex = flex_renderer.render_shop(items)
            return GameResult(text="🏪 每日商店", intent="shop", metadata={"flex_message": flex})
        else:
            return GameResult(text="🏪 商店補貨中，請稍後再來！", intent="shop")
    except Exception as e:
        logger.error(f"Shop failed: {e}", exc_info=True)
        return GameResult(text="⚠️ 商店載入失敗。", intent="shop_error")


# 2. Register Strategies - Chinese Commands FIRST
dispatcher.register(lambda t: t.strip() in ["狀態", "status"], handle_status)
dispatcher.register(lambda t: t.strip() in ["任務", "quests"], handle_quests)
dispatcher.register(lambda t: t.strip() in ["簽到", "checkin"], handle_checkin)
dispatcher.register(lambda t: t.strip() in ["背包", "inventory"], handle_inventory)
dispatcher.register(lambda t: t.strip() in ["商店", "shop"], handle_shop)
dispatcher.register(
    lambda t: "新目標" in t or "設定目標" in t or "設定新目標" in t or t.strip() == "我想設定新目標",
    handle_new_goal,
)


# Placeholder handlers for未實現 features
async def handle_craft(session: AsyncSession, user_id: str, text: str) -> GameResult:
    """Handler for '合成' command."""
    try:
        await container.user_service.get_or_create_user(session, user_id)
        await crafting_service.seed_default_recipes(session)
        recipes = await crafting_service.get_available_recipes(session, user_id)
        flex = flex_renderer.render_crafting_menu(recipes)
        return GameResult(text="🔧 合成介面", intent="craft", metadata={"flex_message": flex})
    except Exception as e:
        logger.error(f"Crafting failed: {e}", exc_info=True)
        return GameResult(text="⚠️ 合成載入失敗。", intent="craft_error")


async def handle_boss(session: AsyncSession, user_id: str, text: str) -> GameResult:
    """Handler for '首領' command."""
    try:
        user = await container.user_service.get_or_create_user(session, user_id)
        boss = await boss_service.get_boss(session, user_id)
        flex = flex_renderer.render_boss_encounter(user, boss)
        status_text = f"👹 首領戰：{boss.name}" if boss else "👹 首領戰：無"
        return GameResult(text=status_text, intent="boss", metadata={"flex_message": flex})
    except Exception as e:
        logger.error(f"Boss load failed: {e}", exc_info=True)
        return GameResult(text="⚠️ 首領系統異常。", intent="boss_error")


async def handle_help(session: AsyncSession, user_id: str, text: str) -> GameResult:
    """Handler for '指令'/'help' command."""
    help_text = (
        "📜 **戰術系統指令清單**\n"
        "------------------\n"
        "📊 **狀態** - 查看屬性與故事進度\n"
        "⚔️ **任務** - 查看今日任務清單\n"
        "✅ **簽到** - 每日領取獎勵\n"
        "🎒 **背包** - 查看金幣與物資\n"
        "🏪 **商店** - 每日隨機商品\n"
        "🎯 **新目標** - 設定新的人生目標\n"
        "🔧 **合成** - (開發中)\n"
        "👹 **首領** - (開發中)\n"
        "------------------\n"
        "💡 直接輸入你想做的事，AI 也會協助你！"
    )
    return GameResult(text=help_text, intent="help")


async def handle_sys_info(session: AsyncSession, user_id: str, text: str) -> GameResult:
    """Handler for '/sys' - System Diagnostics."""
    try:
        import os
        import sqlalchemy
        from sqlalchemy import text as sql_text

        # 1. Version Info
        version = settings.VERSION

        # 2. DB Connection & Schema
        db_status = "Unknown"
        columns = []
        try:
            # Check Connection
            await session.execute(sql_text("SELECT 1"))
            db_status = "Connected"

            # Inspect Schema (for users table)
            # Safe way for AsyncSession? We can try raw SQL for sqlite/pg
            # 'PRAGMA table_info(users)' for sqlite
            # 'SELECT column_name FROM information_schema.columns WHERE table_name='users'' for pg

            # Fallback simple try:
            result = await session.execute(sql_text("SELECT * FROM users LIMIT 1"))
            columns = list(result.keys())

        except Exception as db_e:
            db_status = f"Error: {str(db_e)}"

        msg = (
            f"🔧 **System Diagnostics**\n"
            f"Version: {version}\n"
            f"DB Status: {db_status}\n"
            f"User Columns: {', '.join(columns) if columns else 'N/A'}\n"
            f"Auto-Migrate: {settings.AUTO_MIGRATE}"
        )
        return GameResult(text=msg, intent="sys_info")
    except Exception as e:
        return GameResult(text=f"⚠️ Sys Info Failed: {e}", intent="sys_error")


async def handle_manual_migrate(session: AsyncSession, user_id: str, text: str) -> GameResult:
    """Handler for '/migrate' - Manual Database Migration Trigger."""
    try:
        import io
        import sys
        from alembic import command
        from alembic.config import Config
        from pathlib import Path

        # Capture Stdout/Stderr to return to user
        capture = io.StringIO()
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = capture
        sys.stderr = capture

        try:
            # Setup Alembic Config (Same as run_migrations)
            config_path = Path("alembic.ini").resolve()
            if not config_path.exists():
                # Try finding it relative to app root if CWD is wrong
                config_path = Path(__file__).resolve().parents[2] / "alembic.ini"

            cfg = Config(str(config_path))

            # Need to ensure script_location is absolute if CWD is weird
            # But let's rely on standard config first.
            # Force output to stdout for capture
            cfg.stdout = capture

            command.upgrade(cfg, "head")

            output = capture.getvalue()
            status = "Migration Success"
        except Exception as e:
            output = capture.getvalue() + f"\nEXCEPTION: {e}"
            status = "Migration Failed"
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

        return GameResult(
            text=f"🔧 **{status}**\n\nLogs:\n```\n{output[-1000:]}\n```",  # Last 1000 chars
            intent="sys_migrate",
        )

    except Exception as ie:
        return GameResult(text=f"⚠️ Migration Trigger Failed: {ie}", intent="sys_error")


dispatcher.register(lambda t: t.strip() in ["合成", "craft"], handle_craft)
dispatcher.register(lambda t: t.strip() in ["首領", "boss"], handle_boss)
dispatcher.register(lambda t: t.strip() in ["指令", "help", "說明", "commands"], handle_help)
dispatcher.register(lambda t: t.strip() in ["/sys", "/diag", "系統診斷"], handle_sys_info)
dispatcher.register(lambda t: t.strip() in ["/migrate", "手動遷移"], handle_manual_migrate)


# Chinese Command Priority Routes (Fix: Must be registered BEFORE AI default)
dispatcher.register(lambda t: t.strip() in ["狀態", "status"], handle_status)
dispatcher.register(lambda t: t.strip() in ["任務", "quests"], handle_quests)
dispatcher.register(lambda t: t.strip() in ["簽到", "checkin"], handle_checkin)
dispatcher.register(lambda t: t.strip() in ["背包", "inventory"], handle_inventory)
dispatcher.register(lambda t: t.strip() in ["商店", "shop"], handle_shop)
dispatcher.register(lambda t: "新目標" in t.strip() or "我想設定" in t.strip(), handle_new_goal)

# Legacy
dispatcher.register(lambda t: t.lower().strip() == "attack", handle_attack)
dispatcher.register(lambda t: t.lower().strip() == "defend", handle_defend)

# Default AI
dispatcher.register_default(handle_ai_analysis)


# 3. Expose Core Logic Wrapper
async def process_game_logic(user_id: str, text: str, session: AsyncSession = None) -> GameResult:
    """Core Game Logic Entry Point"""
    if session:
        return await game_loop.process_message(session, user_id, text)

    async with AsyncSessionLocal() as session:
        return await game_loop.process_message(session, user_id, text)


# Include Router
from app.api import line_webhook
from app.api import nerves
from app.api import chat

app.include_router(line_webhook.router, prefix="", tags=["line"])
app.include_router(nerves.router, prefix="/api", tags=["nerves"])
app.include_router(chat.router, prefix="/api", tags=["chat"])


# --- Resilience: Health Check ---
@app.get("/health")
async def health_check():
    health_status = {
        "status": "ok",
        "version": settings.VERSION,
        "database": "unknown",
        "columns": [],
        "timestamp": os.getenv("WEBSITE_HOSTNAME", "local"),
    }
    try:
        async with AsyncSessionLocal() as session:
            # Check Connection
            await session.execute(text("SELECT 1"))
            health_status["database"] = "connected"

            # Check Schema
            try:
                result = await session.execute(text("SELECT * FROM users LIMIT 1"))
                columns = list(result.keys())
                health_status["columns"] = columns
            except Exception:
                health_status["columns"] = ["error_reading_cols"]

    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
        logging.error(f"Health Check Failed: {e}", exc_info=True)

    return health_status


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
