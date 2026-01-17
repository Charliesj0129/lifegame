from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from application.services.quest_service import quest_service
from app.models.quest import QuestStatus
import random


class HelpService:
    async def get_dynamic_help(self, session: AsyncSession, user: User) -> dict:
        """
        Analyzes user state and returns a context-aware help object.
        Returns dict: {"title": str, "message": str, "suggestion": str, "action_label": str, "action_data": str}
        """
        tips = []

        # 1. Critical State (Health)
        if user.hp < 30:
            tips.append(
                {
                    "priority": 100,
                    "title": "🩸 生命危急",
                    "message": "你的生命值低於 30%！如果現在倒下，可能會失去經驗值。",
                    "suggestion": "建議立刻休息 (輸入 'Rest') 或使用藥水。",
                    "action_label": "❤️ 使用藥水",
                    "action_data": "action=use_item&item_id=ITEM_POTION",
                }
            )

        # 2. Hollowing (Inactivity)
        if user.is_hollowed:
            tips.append(
                {
                    "priority": 95,
                    "title": "💀 活屍化警告",
                    "message": "你已很久沒有行動，正處於活屍化邊緣。",
                    "suggestion": "完成任意一個任務或習慣來恢復人性。",
                    "action_label": "📜 查看任務",
                    "action_data": "action=quest_list",
                }
            )

        # 3. Quest Status
        active_quests = await quest_service.get_daily_quests(session, user.id)
        pending_count = sum(1 for q in active_quests if q.status == QuestStatus.PENDING.value)

        if pending_count > 0:
            tips.append(
                {
                    "priority": 80,
                    "title": "⚔️ 任務等待中",
                    "message": f"你還有 {pending_count} 個每日任務尚未完成。",
                    "suggestion": "完成任務是獲取經驗值最快的方法。",
                    "action_label": "📜 查看任務",
                    "action_data": "action=quest_list",
                }
            )
        elif not active_quests:
            tips.append(
                {
                    "priority": 70,
                    "title": "✨ 新的一天",
                    "message": "今天還沒有生成任務嗎？",
                    "suggestion": "生成每日任務來開始今天的冒險。",
                    "action_label": "🎲 生成任務",
                    "action_data": "action=reroll_quests",
                }
            )

        # 4. Streak
        if user.streak_count > 2:
            tips.append(
                {
                    "priority": 50,
                    "title": "🔥 連勝狀態",
                    "message": f"你已經連續 {user.streak_count} 天保持活躍！",
                    "suggestion": "保持下去，連續 7 天將獲得稀有獎勵。",
                    "action_label": "📊 查看個人檔案",
                    "action_data": "action=profile",
                }
            )

        # 5. Generic / Default
        default_tips = [
            {
                "title": "💡 探索世界",
                "message": "不知道做什麼？試著輸入任何行動，如 'Read book' 或 'Pushups'。",
                "suggestion": "系統會自動分析你的意圖並給予獎勵。",
                "action_label": "❓ 顯示指令",
                "action_data": "action=manual",  # TBD
            },
            {
                "title": "🏪 商店與合成",
                "message": "金幣可以用來購買裝備，或合成更強的道具。",
                "suggestion": "檢查你的庫存，或許有可以合成的材料。",
                "action_label": "🎒 查看庫存",
                "action_data": "action=inventory",
            },
        ]

        # Sort by priority and pick top
        if tips:
            # Sort desc by priority
            tips.sort(key=lambda x: x["priority"], reverse=True)
            return tips[0]
        else:
            return random.choice(default_tips)


help_service = HelpService()
