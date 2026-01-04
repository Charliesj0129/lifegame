import logging
import random
from datetime import date
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.quest import Quest, QuestStatus, Rival
from app.services.line_bot import get_messaging_api
from linebot.v3.messaging import FlexMessage, FlexContainer, TextMessage, PushMessageRequest, QuickReply, QuickReplyItem, MessageAction, PostbackAction

from app.services.persona_service import persona_service
from app.services.audio_service import audio_service

logger = logging.getLogger(__name__)

class DailyBriefingService:
    async def process_daily_briefing(self, user_id: str):
        async with AsyncSessionLocal() as session:
            # Get User
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()
            if not user:
                return

            rival = await self._update_rival(session, user_id, user.level)
            
            result = await session.execute(
                select(Quest).where(
                    Quest.user_id == user_id,
                    Quest.status.in_([QuestStatus.ACTIVE.value, QuestStatus.PENDING.value])
                )
            )
            quests = result.scalars().all()
            
            flex_message = self._create_briefing_flex(user, rival, quests)
            
            # Audio Briefing
            audio_msg = audio_service.get_briefing_audio()
            # audio_msg.sender = persona_service.get_sender_object(persona_service.VIPER)
            
            try:
                api = get_messaging_api()
                if api:
                    await api.push_message(
                        PushMessageRequest(
                            to=user_id,
                            messages=[audio_msg, flex_message]
                        )
                    )
                    logger.info(f"Daily Briefing pushed to {user_id}")
            except Exception as e:
                logger.error(f"Failed to push briefing: {e}")

    async def _update_rival(self, session: AsyncSession, user_id: str, user_level: int) -> Rival:
        result = await session.execute(select(Rival).where(Rival.user_id == user_id))
        rival = result.scalars().first()
        
        if not rival:
            rival = Rival(user_id=user_id, name="Viper", level=max(1, user_level), xp=0)
            session.add(rival)
        
        # Viper Logic: Grows 20-50% of a level per day + some randomness
        growth = random.randint(30, 80) # XP
        rival.xp += growth
        if rival.xp >= 500:
            rival.level += 1
            rival.xp -= 500
            
        await session.commit()
        await session.refresh(rival)
        return rival

    def _create_briefing_flex(self, user: User, rival: Rival, quests: list[Quest]) -> FlexMessage:
        # P5 Style Header
        header_color = "#FF0000" if rival.level > user.level else "#000000"
        
        quest_items = []
        for q in quests[:3]:
            status_icon = "🔥" if q.status == "ACTIVE" else "⏳"
            quest_items.append({
                "type": "box",
                "layout": "baseline",
                "contents": [
                    {"type": "text", "text": status_icon, "flex": 1, "size": "sm"},
                    {"type": "text", "text": q.title, "flex": 5, "size": "sm", "wrap": True},
                    {"type": "text", "text": f"{q.difficulty_tier}", "flex": 1, "size": "xs", "color": "#aaaaaa", "align": "end"}
                ]
            })

        contents = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "DAILY BRIEFING", "weight": "bold", "color": "#ffffff", "size": "xl"},
                    {"type": "text", "text": f"OP: {user.id[:8]}...", "color": "#ffffff", "size": "xs"}
                ],
                "backgroundColor": header_color
            },
            "hero": {
                "type": "image",
                "url": "https://images.unsplash.com/photo-1550751827-4bd374c3f58b",
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": f"⚠️ VIPER STATUS (Lv.{rival.level})", "weight": "bold", "color": "#ff5555", "size": "sm"},
                            {"type": "text", "text": f"Lead: +{max(0, (rival.level - user.level)*500 + (rival.xp - (user.xp or 0)))} XP", "size": "xs", "color": "#aaaaaa"}
                        ],
                        "margin": "md"
                    },
                    {"type": "separator", "margin": "lg"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": "ACTIVE MISSION PROTOCOLS", "weight": "bold", "margin": "lg", "size": "sm"},
                        ] + quest_items,
                        "margin": "sm"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                     {"type": "button", "action": {"type": "message", "label": "🌅 Start Morning Routine", "text": "Start Morning Routine"}, "style": "primary", "color": "#000000"}
                ]
            }
        }
        
        # Quick Replies for Interactions
        quick_reply = QuickReply(
            items=[
                QuickReplyItem(
                    action=PostbackAction(label="🔄 Reroll Quests", data="action=reroll_quests", display_text="Rerolling Quests...")
                ),
                QuickReplyItem(
                    action=PostbackAction(label="✅ Accept All", data="action=accept_all_quests", display_text="Accepting All...")
                ),
                QuickReplyItem(
                    action=PostbackAction(label="⏭️ Skip Viper", data="action=skip_rival_update", display_text="Skipping Viper Update")
                )
            ]
        )
        
        return FlexMessage(
            alt_text="Daily Briefing", 
            contents=FlexContainer.from_dict(contents),
            quick_reply=quick_reply,
            sender=persona_service.get_sender_object(persona_service.VIPER)
        )

daily_briefing = DailyBriefingService()
