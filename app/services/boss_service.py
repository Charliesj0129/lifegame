from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.gamification import Boss, BossStatus
from app.services.ai_service import ai_engine
from app.services.rival_service import rival_service
import random

class BossService:
    async def get_active_boss(self, session: AsyncSession, user_id: str) -> Boss:
        stmt = select(Boss).where(
            Boss.user_id == user_id,
            Boss.status == BossStatus.ACTIVE
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def spawn_boss(self, session: AsyncSession, user_id: str):
        # Check if already active
        if await self.get_active_boss(session, user_id):
            return "Boss already active."

        # Get Rival context for flavor
        try:
            rival = await rival_service.get_rival(session, user_id)
            if rival:
                # Proactive Nuance: Generate Boss Name based on Rival
                prompt = f"Rival Level {rival.level}. Generate a RPG Boss Name related to procrastination or laziness."
                json_resp = await ai_engine.generate_json(
                    "You are a game master. JSON: {'boss_name': 'str'}", prompt
                )
                boss_name = json_resp.get("boss_name", "The Procrastinator")
            else:
                boss_name = "Shadow of Sloth"
        except Exception:
             boss_name = "Shadow of Sloth"

        new_boss = Boss(
            user_id=user_id,
            name=boss_name,
            hp=1000,
            max_hp=1000,
            level=5,
            status=BossStatus.ACTIVE
        )
        session.add(new_boss)
        await session.commit()
        return f"⚠️ BOSS SPAWNED: {boss_name} (1000 HP)"

    async def deal_damage(self, session: AsyncSession, user_id: str, damage: int):
        boss = await self.get_active_boss(session, user_id)
        if not boss:
            return None

        boss.hp -= damage
        msg = f"⚔️ Dealt {damage} dmg to {boss.name}!"

        if boss.hp <= 0:
            boss.hp = 0
            boss.status = BossStatus.DEFEATED
            msg += f"\n🏆 {boss.name} DEFEATED! +500 Gold!"
            
            # Grant rewards (Direct User modification for now, ideally via user_service)
            from app.models.user import User
            user = await session.get(User, user_id)
            if user:
                user.gold = (user.gold or 0) + 500
        
        await session.commit()
        return msg

    async def generate_attack_challenge(self) -> str:
        # Static for MVP or AI-generated
        challenges = [
            "Do 20 Pushups NOW!",
            "Drink a glass of water!",
            "Meditate for 1 minute!",
            "Clean your desk immediately!"
        ]
        return random.choice(challenges)

boss_service = BossService()
