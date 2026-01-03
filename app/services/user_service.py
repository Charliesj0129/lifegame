from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.models.action_log import ActionLog
from app.services.accountant import accountant
from app.services.ai_engine import ai_engine
from app.services.loot_service import loot_service
from app.services.inventory_service import inventory_service
import logging

logger = logging.getLogger(__name__)

from app.schemas.game_schemas import ProcessResult

class UserService:
    async def get_or_create_user(self, session: AsyncSession, line_user_id: str, name: str = "Unknown") -> User:
        result = await session.execute(select(User).where(User.id == line_user_id))
        user = result.scalars().first()
        if not user:
            user = User(id=line_user_id, name=name)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user

    async def get_user(self, session: AsyncSession, line_user_id: str) -> User | None:
        result = await session.execute(select(User).where(User.id == line_user_id))
        return result.scalars().first()

    async def process_action(self, session: AsyncSession, line_user_id: str, text: str) -> ProcessResult:
        import time
        t_start = time.time()
        
        # 1. Get User
        user = await self.get_or_create_user(session, line_user_id)
        
        # 2. Fast/Slow Router (System 1 vs System 2)
        t_ai_start = time.time()
        
        # Fast Mode Criteria
        is_fast_mode = False
        ai_result = {}
        
        normalized_text = text.lower().strip()
        if len(text) < 15:
            if any(k in normalized_text for k in ["gym", "run", "lift", "workout", "str"]):
                ai_result = {"stat_type": "STR", "difficulty_tier": "C", "narrative": "⚡ [System 1] Muscle fiber damage detected. Growth initiated.", "loot_drop": {"has_loot": False}}
                is_fast_mode = True
            elif any(k in normalized_text for k in ["study", "code", "read", "learn", "int"]):
                ai_result = {"stat_type": "INT", "difficulty_tier": "C", "narrative": "⚡ [System 1] Neural pathways reinforced. Synapse firing rate up.", "loot_drop": {"has_loot": False}}
                is_fast_mode = True
            elif any(k in normalized_text for k in ["sleep", "eat", "rest", "food", "vit"]):
                ai_result = {"stat_type": "VIT", "difficulty_tier": "D", "narrative": "⚡ [System 1] Biological systems repairing. Homeostasis restoring.", "loot_drop": {"has_loot": False}}
                is_fast_mode = True
                
        if not is_fast_mode:
             # Slow Mode (Deep Thought)
             ai_result = await ai_engine.analyze_action(text)
             
        t_ai_end = time.time()
        
        attribute = ai_result.get("stat_type", "VIT")
        difficulty = ai_result.get("difficulty_tier", "E")
        narrative = ai_result.get("narrative", "Data Uploaded.")
        has_loot = ai_result.get("loot_drop", {}).get("has_loot", False)
        
        # 3. Accountant Math (Central Authority for Balance)
        raw_xp = accountant.calculate_xp(attribute, difficulty)
        
        # Apply Buffs
        active_buffs = await inventory_service.get_active_buffs(session, user.id)
        xp_gain = accountant.apply_buffs(raw_xp, active_buffs, attribute)
        
        old_level = user.level
        accountant.apply_xp(user, attribute, xp_gain)
        
        # 4. Persistence
        log = ActionLog(
            user_id=user.id,
            action_text=text,
            attribute_tag=attribute,
            difficulty_tier=difficulty,
            xp_gained=xp_gain
        )
        session.add(log)
        
        # M6: Update Streak
        from datetime import datetime, timedelta
        now = datetime.now()
        
        if not user.last_active_date:
            user.streak_count = 1
        else:
            last_date = user.last_active_date.date()
            today_date = now.date()
            
            if last_date == today_date:
                pass # Already active today
            elif last_date == (today_date - timedelta(days=1)):
                user.streak_count += 1 # Consecutive day
            else:
                user.streak_count = 1 # Broken streak
        
        user.last_active_date = now
        session.add(user)
        await session.commit()
        t_db_end = time.time()
        
        # 5. Loot Handling (AI decides IF, Code decides WHAT)
        loot_name = None
        loot_rarity = None
        
        loot_item = await loot_service.calculate_drop(session, difficulty, force_drop=has_loot)
        if loot_item:
            await loot_service.grant_item(session, user.id, loot_item)
            loot_name = loot_item.name
            loot_rarity = loot_item.rarity.value
            
        total_time = (time.time() - t_start) * 1000
        ai_time = (t_ai_end - t_ai_start) * 1000
        db_time = (t_db_end - t_ai_end) * 1000
        logger.info(f"PERF: Total={total_time:.0f}ms | AI={ai_time:.0f}ms | DB={db_time:.0f}ms")

        # 6. Response Construction
        msg = f"{narrative}\n\n[SYSTEM] {attribute} +{xp_gain} XP"
        
        if loot_name:
             msg += f"\n🎁 LOOT: {loot_name} ({loot_rarity})"

        if user.level > old_level:
            msg += f"\n🎉 LEVEL UP! You are now Lv.{user.level}!"
            
        
        # Determine Title
        title = "Street Rat"
        if user.level >= 5: title = "Runner"
        if user.level >= 10: title = "Street Samurai"
        if user.level >= 20: title = "Cyberlegend"
        if user.streak_count >= 3: title = f"🔥 {title}"

        return ProcessResult(
            text=msg,
            user_id=user.id,
            action_text=text,
            attribute=attribute,
            xp_gained=xp_gain,
            new_level=user.level,
            leveled_up=(user.level > old_level),
            loot_name=loot_name,
            loot_rarity=loot_rarity,
            narrative=narrative,
            current_attributes={
                "STR": user.str, "INT": user.int, "VIT": user.vit, "WIS": user.wis, "CHA": user.cha
            },
            current_xp=user.xp or 0,
            streak_count=user.streak_count,
            user_title=title
        )

user_service = UserService()
