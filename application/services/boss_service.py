from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.gamification import Boss, BossStatus
from application.services.ai_service import ai_engine
from application.services.rival_service import rival_service
import random


class BossService:
    async def get_active_boss(self, session: AsyncSession, user_id: str) -> Boss:
        stmt = select(Boss).where(Boss.user_id == user_id, Boss.status == BossStatus.ACTIVE)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def spawn_boss(self, session: AsyncSession, user_id: str):
        # Check if already active
        if await self.get_active_boss(session, user_id):
            return "首領已存在。"

        # Get Rival context for flavor
        try:
            rival = await rival_service.get_rival(session, user_id)
            if rival:
                # Proactive Nuance: Generate Boss Name based on Rival
                prompt = f"對手等級 {rival.level}。生成一個與拖延或惰性相關的 RPG 首領名稱。"
                json_resp = await ai_engine.generate_json("你是遊戲主宰。輸出 JSON: {'boss_name': 'str'}", prompt)
                boss_name = json_resp.get("boss_name", "惰性之影")
            else:
                boss_name = "惰性之影"
        except Exception:
            boss_name = "惰性之影"

        new_boss = Boss(
            user_id=user_id,
            name=boss_name,
            hp=1000,
            max_hp=1000,
            level=5,
            status=BossStatus.ACTIVE,
        )
        session.add(new_boss)
        await session.commit()
        return f"⚠️ 首領現身：{boss_name}（1000 HP）"

    async def deal_damage(self, session: AsyncSession, user_id: str, damage: int):
        boss = await self.get_active_boss(session, user_id)
        if not boss:
            return None

        boss.hp -= damage
        msg = f"⚔️ 造成 {damage} 傷害：{boss.name}"

        if boss.hp <= 0:
            boss.hp = 0
            boss.status = BossStatus.DEFEATED
            msg += f"\n🏆 擊敗 {boss.name}！獲得 500 金幣！"

            # Grant rewards (Direct User modification for now, ideally via user_service)
            from app.models.user import User

            user = await session.get(User, user_id)
            if user:
                user.gold = (user.gold or 0) + 500

            # --- Graph Sync ---
            try:
                from app.core.container import container

                adapter = container.graph_service.adapter

                if adapter:
                    # Ensure Boss Node
                    await adapter.add_node("Boss", {"id": str(boss.id), "name": boss.name, "level": str(boss.level)})

                    import datetime

                    await adapter.add_relationship(
                        "User",
                        user_id,
                        "DEFEATED",
                        "Boss",
                        str(boss.id),
                        {"timestamp": datetime.datetime.now().isoformat()},
                        from_key_field="id",
                        to_key_field="id",
                    )
            except Exception as e:
                print(f"Graph Sync Failed: {e}")

        await session.commit()
        return msg

    async def generate_attack_challenge(self) -> str:
        # Static for MVP or AI-generated
        challenges = [
            "立刻做 20 下伏地挺身！",
            "喝一杯水！",
            "冥想 1 分鐘！",
            "馬上整理桌面！",
        ]
        return random.choice(challenges)


boss_service = BossService()
