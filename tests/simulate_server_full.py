import asyncio
import logging
from unittest.mock import AsyncMock, patch
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.api.webhook import handle_message, handle_postback
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent,
    PostbackContent,
    UserSource,
)
from linebot.v3.messaging import TextMessage, FlexMessage
from app.core.database import engine
from app.models.base import Base

# Import all models for registry
from legacy.models.quest import Quest

# Setup Logger
logging.basicConfig(level=logging.ERROR)  # Quiet execution
logger = logging.getLogger("simulation")


async def setup_db():
    print("Initializing In-Memory Database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def simulate_flow():
    await setup_db()

    print("\n🚀 STARTING LOCAL SIMULATION 🚀")

    # Mock Dependencies
    # We use REAL DB (via get_db default behavior using engine), but we MOCK API and AI.

    with (
        patch("app.api.webhook.get_messaging_api") as mock_get_api,
        patch(
            "legacy.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock
        ) as mock_ai,
    ):

        # Setup AI Mock
        mock_ai.return_value = {
            "milestones": [
                {"title": "Simulated Milestone", "difficulty": "B", "desc": "Big Step"}
            ],
            "daily_habits": [{"title": "Daily Habit", "desc": "Do it"}],
            "quests": [
                {"title": "AI Task 1", "desc": "Do this", "diff": "D", "xp": 20},
                {"title": "AI Task 2", "desc": "Do that", "diff": "E", "xp": 10},
                {"title": "AI Task 3", "desc": "Do other", "diff": "C", "xp": 30},
            ],
        }

        # Setup API Mock to print replies instead of sending
        mock_api_instance = AsyncMock()
        mock_get_api.return_value = mock_api_instance

        async def mock_reply(request):
            print(f"\n🤖 BOT REPLY (To: {request.reply_token}):")
            for msg in request.messages:
                if isinstance(msg, TextMessage):
                    print(f"   [TEXT] {msg.text}")
                elif isinstance(msg, FlexMessage):
                    print(f"   [FLEX] Alt Text: {msg.alt_text}")
                    # We could dump the JSON here to inspect UI
                    # print(msg.contents)

        mock_api_instance.reply_message.side_effect = mock_reply

        # --- SCENARIO 1: STATUS (Creates User) ---
        print("\n👤 USER: 'Status'")
        event = MessageEvent(
            source=UserSource(userId="U_SIM"),
            replyToken="tk_status",
            message=TextMessageContent(id="msg_1", text="Status", quoteToken="qt_1"),
            mode="active",
            timestamp=1234567890,
            webhookEventId="id_1",
            deliveryContext={"isRedelivery": False},
        )
        await handle_message(event)

        # --- SCENARIO 2: NEW GOAL ---
        print("\n👤 USER: '/new_goal Become a local legend'")
        event.message = TextMessageContent(
            id="msg_2", text="/new_goal Become a local legend", quoteToken="qt_2"
        )
        event.reply_token = "tk_goal"
        await handle_message(event)

        # --- SCENARIO 3: CHECK QUESTS ---
        print("\n👤 USER: 'Quests'")
        event.message = TextMessageContent(id="msg_3", text="Quests", quoteToken="qt_3")
        event.reply_token = "tk_quests"
        await handle_message(event)

        # --- SCENARIO 4: COMPLETE QUEST (Postback) ---
        # We need to find the Quest ID created in Scenario 3
        # Since we use real DB, we can query it!
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Quest).where(Quest.user_id == "U_SIM")
            )
            quests = result.scalars().all()
            if quests:
                q = quests[0]
                print(f"\n👤 USER: [CLICK] Complete Quest {q.title} (ID: {q.id})")
                pb_event = PostbackEvent(
                    source=UserSource(userId="U_SIM"),
                    replyToken="tk_pb",
                    postback=PostbackContent(
                        data=f"action=complete_quest&quest_id={q.id}"
                    ),
                    mode="active",
                    timestamp=1234567890,
                    webhookEventId="id_2",
                    deliveryContext={"isRedelivery": False},
                )
                await handle_postback(pb_event)
            else:
                print("⚠️ No quests found in DB to complete.")

        # --- SCENARIO 5: MORNING ROUTINE (From Rich Menu) ---
        print(
            "\n👤 USER: [MENU] 'Start Morning Routine' (Payload: 'Start Morning Routine')"
        )
        event.message = TextMessageContent(
            id="msg_4", text="Start Morning Routine", quoteToken="qt_4"
        )
        event.reply_token = "tk_morning"
        await handle_message(event)


if __name__ == "__main__":
    asyncio.run(simulate_flow())
