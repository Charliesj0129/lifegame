import logging
import datetime
from sqlalchemy.future import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.quest import Quest, QuestStatus, Rival
from app.services.line_bot import get_messaging_api
from linebot.v3.messaging import FlexMessage, FlexContainer, PushMessageRequest, QuickReply, QuickReplyItem, PostbackAction

from app.services.persona_service import persona_service
from app.services.audio_service import audio_service
from app.services.rival_service import rival_service
from app.models.dda import DailyOutcome

logger = logging.getLogger(__name__)

class DailyBriefingService:
    async def process_daily_briefing(self, user_id: str):
        async with AsyncSessionLocal() as session:
            # Get User
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()
            if not user:
                return

            rival = await rival_service.advance_daily_briefing(session, user)
            
            result = await session.execute(
                select(Quest).where(
                    Quest.user_id == user_id,
                    Quest.status.in_([QuestStatus.ACTIVE.value, QuestStatus.PENDING.value])
                )
            )
            quests = result.scalars().all()
            
            dda_hint = None
            yesterday = datetime.date.today() - datetime.timedelta(days=1)
            outcome_stmt = select(DailyOutcome).where(
                DailyOutcome.user_id == user_id,
                DailyOutcome.is_global.is_(True),
                DailyOutcome.date == yesterday
            )
            outcome = (await session.execute(outcome_stmt)).scalars().first()
            if outcome and not outcome.done:
                dda_hint = "偵測到能量低落：今日任務已降階，先穩住連勝。"

            flex_message = self._create_briefing_flex(user, rival, quests, dda_hint=dda_hint)
            
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

    def _create_briefing_flex(self, user: User, rival: Rival, quests: list[Quest], dda_hint: str | None = None) -> FlexMessage:
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
                    {"type": "text", "text": f"難度 {q.difficulty_tier}", "flex": 1, "size": "xs", "color": "#aaaaaa", "align": "end"}
                ]
            })

        contents = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "每日簡報", "weight": "bold", "color": "#ffffff", "size": "xl"},
                    {"type": "text", "text": f"代號：{user.id[:8]}...", "color": "#ffffff", "size": "xs"}
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
                "contents": (
                    ([{"type": "text", "text": dda_hint, "size": "xs", "color": "#ffcc00", "wrap": True}] if dda_hint else [])
                    + [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": f"⚠️ Viper 狀態（Lv.{rival.level}）", "weight": "bold", "color": "#ff5555", "size": "sm"},
                            {"type": "text", "text": f"領先：+{max(0, (rival.level - user.level)*500 + (rival.xp - (user.xp or 0)))} 經驗", "size": "xs", "color": "#aaaaaa"}
                        ],
                        "margin": "md"
                    },
                    {"type": "separator", "margin": "lg"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": "今日任務指令", "weight": "bold", "margin": "lg", "size": "sm"},
                        ] + quest_items,
                        "margin": "sm"
                    }
                    ]
                )
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                     {"type": "button", "action": {"type": "message", "label": "🌅 開始今日任務", "text": "開始今日任務"}, "style": "primary", "color": "#000000"}
                ]
            }
        }
        
        # Quick Replies for Interactions
        quick_reply = QuickReply(
            items=[
                QuickReplyItem(
                    action=PostbackAction(label="🔄 重新生成", data="action=reroll_quests", display_text="重新生成任務...")
                ),
                QuickReplyItem(
                    action=PostbackAction(label="✅ 全部接受", data="action=accept_all_quests", display_text="全部接受任務...")
                ),
                QuickReplyItem(
                    action=PostbackAction(label="⏭️ 略過 Viper", data="action=skip_rival_update", display_text="略過 Viper 更新")
                )
            ]
        )
        
        return FlexMessage(
            alt_text="每日簡報", 
            contents=FlexContainer.from_dict(contents),
            quick_reply=quick_reply,
            sender=persona_service.get_sender_object(persona_service.VIPER)
        )

daily_briefing = DailyBriefingService()
