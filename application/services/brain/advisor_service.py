import logging
from application.services.ai_engine import ai_engine

logger = logging.getLogger(__name__)


class AdvisorService:
    """
    Handles Coaching, Reports, and Habit Optimization Advice.
    """

    async def generate_weekly_report(self, session, user_id: str) -> dict:
        """
        F5: Generates a weekly performance review.
        """
        from application.services.quest_service import quest_service

        # Fetch week's completed quests
        quests = await quest_service.get_completed_quests_this_week(session, user_id)
        xp_total = sum(q.xp_reward or 0 for q in quests)
        quest_count = len(quests)

        # Grade calculation
        if quest_count >= 21:
            grade = "S"
        elif quest_count >= 14:
            grade = "A"
        elif quest_count >= 10:
            grade = "B"
        elif quest_count >= 7:
            grade = "C"
        elif quest_count >= 3:
            grade = "D"
        else:
            grade = "F"

        # AI summary
        try:
            result = await ai_engine.generate_json(
                "Generate a brief weekly review in Traditional Chinese. Output JSON: {'summary': 'str', 'suggestions': ['str']}",
                f"User completed {quest_count} quests for {xp_total} XP. Grade: {grade}.",
            )
            summary = result.get("summary", f"本週完成 {quest_count} 任務。")
            suggestions = result.get("suggestions", [])
        except Exception as e:
            logger.warning(f"Weekly report AI failed: {e}")
            summary = f"本週完成 {quest_count} 任務，獲得 {xp_total} XP。"
            suggestions = []

        return {"grade": grade, "summary": summary, "xp_total": xp_total, "suggestions": suggestions}

    async def suggest_habit_stack(self, session, user_id: str) -> str:
        """
        F9: AI analyzes habit logs and suggests stacking optimizations.
        """
        from application.services.quest_service import quest_service

        # Fetch recent habit completions
        habits = await quest_service.get_daily_habits(session, user_id)
        habit_names = [h.habit_name or h.habit_tag for h in habits if h] if habits else []

        if len(habit_names) < 2:
            return "目前習慣數量不足，建議先建立至少兩個習慣。"

        try:
            result = await ai_engine.generate_json(
                """You are a behavioral optimization coach.
Analyze these habits and suggest a "habit stacking" strategy.
Output JSON: {"suggestion": "A brief actionable suggestion in Traditional Chinese"}
""",
                f"User's habits: {', '.join(habit_names)}",
            )
            return result.get("suggestion", "建議將習慣串聯執行以提高成功率。")
        except Exception as e:
            logger.warning(f"Habit stack suggestion failed: {e}")
            return "建議將成功率高的習慣放在前面，新習慣緊接其後。"
