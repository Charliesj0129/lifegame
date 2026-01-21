from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class TitleService:
    async def get_user_title(self, session: AsyncSession, user: User) -> str:
        """
        Determines the user's current title based on stats.
        """
        level = user.level or 1
        streak = user.streak_count or 0

        # Base Title by Level
        if level >= 50:
            title = "覺醒者 (Awakened)"
        elif level >= 30:
            title = "都會傳奇 (Urban Legend)"
        elif level >= 20:
            title = "賽博幹部 (Cyber Exec)"
        elif level >= 10:
            title = "街頭武士 (Street Samurai)"
        elif level >= 5:
            title = "暗影跑者 (Shadow Runner)"
        else:
            title = "未登錄市民 (Citizen)"

        # Suffix by Streak
        if streak >= 30:
            title += " 🔥[不滅之火]"
        elif streak >= 14:
            title += " 🔥[堅持者]"
        elif streak >= 7:
            title += " 🔥[專注]"

        # Prefix by Class (Highest Stat)
        stats = {
            "STR": user.str or 0,
            "INT": user.int or 0,
            "VIT": user.vit or 0,
            "WIS": user.wis or 0,
            "CHA": user.cha or 0,
        }
        highest_stat = max(stats, key=stats.get)
        val = stats[highest_stat]

        prefix = ""
        if val >= 20:  # Only if stat is significant
            if highest_stat == "STR":
                prefix = "強襲型 "
            if highest_stat == "INT":
                prefix = "邏輯型 "
            if highest_stat == "VIT":
                prefix = "重裝型 "
            if highest_stat == "WIS":
                prefix = "戰略型 "
            if highest_stat == "CHA":
                prefix = "交涉型 "

        return f"{prefix}{title}"


title_service = TitleService()
