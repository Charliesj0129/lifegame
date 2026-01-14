import logging
import uuid
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.game_result import GameResult
from legacy.services.user_service import user_service
from legacy.services.persona_service import persona_service
from legacy.services.audio_service import audio_service
from legacy.services.rival_service import rival_service
from legacy.services.hp_service import hp_service

# Dispatcher is imported inside method to avoid circular imports during refactor?
# Or just import it. app.core.dispatcher imports services, so check cycles.
# Dispatcher -> Service -> Database. GameLoop -> Dispatcher. Should be fine.
from app.core.dispatcher import dispatcher

logger = logging.getLogger(__name__)


class GameLoop:
    """
    Orchestrates the Main Game Loop:
    1. Load User
    2. Check Vitals (HP/Hollowed)
    3. Check Environment (Rival/Nemesis)
    4. Process Input (Dispatch)
    5. Synthesize Output (Narrative + Meta)
    """

    async def process_message(self, session: AsyncSession, user_id: str, text: str) -> GameResult:
        try:
            # 1. Get User
            user = await user_service.get_or_create_user(session, user_id)
            # Ensure optional fields exist to avoid render crashes
            if not hasattr(user, "job_class") or getattr(user, "job_class", None) is None:
                setattr(user, "job_class", "Novice")

            # 2. Vitals Check (Hollowed)
            is_hollowed = getattr(user, "is_hollowed", False) is True
            hp_status = getattr(user, "hp_status", "")

            if is_hollowed or hp_status == "HOLLOWED":
                rescue_msg = await hp_service.trigger_rescue_protocol(session, user)
                return GameResult(
                    text=f"⚠️ 瀕死狀態啟動。\n{rescue_msg}",
                    intent="hollowed_rescue",
                    metadata={"sender": persona_service.SYSTEM},
                )

            # 3. Environment (Rival)
            rival_log = ""
            try:
                rival_log = await rival_service.process_encounter(session, user)
            except Exception as e:
                logger.warning(f"Rival encounter failed: {e}")

            # 4. Dispatch Input
            result_obj = await dispatcher.dispatch(session, user_id, text)

            # 5. Normalize Result
            # Logic similar to what we did in webhook refactor, but cleaner.
            game_result = self._normalize_result(result_obj)

            # 6. Apply Context (Rival Log)
            if rival_log:
                if game_result.text:
                    game_result.text = f"{rival_log}\n\n{game_result.text}"
                else:
                    game_result.text = rival_log

            # 7. Apply Persona Hint (if not already set)
            if not game_result.metadata:
                game_result.metadata = {}

            # Determine Intent Tool (for persona selection)
            # We need to extract intent from result if dispatch didn't return it clearly
            # Legacy dispatcher returns (msg, tool, data).
            # _normalize_result handles extraction.
            intent = game_result.intent

            # Persona Logic
            if intent == "hollowed_rescue":
                sender = persona_service.SYSTEM
            elif intent == "get_status":
                from legacy.services.lore_service import lore_service
                from legacy.services.flex_renderer import flex_renderer

                lore_prog = await lore_service.get_user_progress(session, user_id)
                flex_msg = flex_renderer.render_status(user, lore_prog)

                game_result.metadata["flex_message"] = flex_msg
                game_result.text = "Status Update"
                sender = persona_service.SYSTEM

            elif intent == "get_quests":
                from legacy.services.quest_service import quest_service
                from legacy.services.flex_renderer import flex_renderer

                quests = await quest_service.get_daily_quests(session, user_id)
                habits = await quest_service.get_daily_habits(session, user_id)
                flex_msg = flex_renderer.render_quest_list(quests, habits)

                game_result.metadata["flex_message"] = flex_msg
                game_result.text = "Quest List"
                sender = persona_service.SYSTEM

            elif intent == "get_inventory":
                sender = persona_service.SYSTEM
            elif intent in ["set_goal", "use_item"]:
                sender = persona_service.MENTOR
            else:
                sender = persona_service.SYSTEM

            game_result.metadata["sender"] = sender

            # 8. Side Effects (Audio)
            # Check for level up in result metadata
            if game_result.metadata.get("leveled_up"):
                # Ideally return audio url or signal in Result
                # Legacy code: messages_to_send.append(audio_service.get_level_up_audio())
                # We put it in metadata["audio_message"]?
                # Or "extra_messages". LineClient needs to handle this.
                fanfare = audio_service.get_level_up_audio()
                game_result.metadata["audio_message"] = fanfare

            # Rival Taunt Support?
            # Legacy code: if rival_log, explicitly append Viper msg if response was NOT text.
            # Here we already prepended rival_log to text.
            # If main response is Image/Flex, we can't prepend text.
            # So if GameResult has image_url or flex_message, we put rival_log in metadata["extra_text"]?
            # Or simplified: Start with Text(rival_log), then Image.
            # Let's use metadata["pre_message"] = rival_log.

            if rival_log and (game_result.image_url or game_result.metadata.get("flex_message")):
                # We can't merge text into image/flex.
                game_result.metadata["pre_text"] = rival_log
                game_result.metadata["pre_sender"] = persona_service.VIPER

            return game_result

        except Exception as e:
            logger.error(f"GameLoop Error: {e}", exc_info=True)
            error_hash = uuid.uuid4().hex[:8]
            return GameResult(text=f"⚠️ 系統異常 ({error_hash})", metadata={"sender": persona_service.SYSTEM})

    def _normalize_result(self, result_obj: Any) -> GameResult:
        if isinstance(result_obj, GameResult):
            return result_obj

        intent = "unknown"
        meta = {}

        if isinstance(result_obj, tuple):
            # (msg, tool, data)
            msg = result_obj[0]
            intent = result_obj[1] if len(result_obj) > 1 else "unknown"
            meta = result_obj[2] if len(result_obj) > 2 else {}
        else:
            msg = result_obj

        # Convert Msg -> Text or Metadata
        from linebot.v3.messaging import TextMessage, FlexMessage

        text = ""
        flex = None

        if isinstance(msg, TextMessage):
            text = msg.text
        elif isinstance(msg, FlexMessage):
            flex = msg
            text = "Flex Message"  # Fallback text?
        elif hasattr(msg, "type") and msg.type == "flex":
            # Container object
            flex = msg
        else:
            text = str(msg)

        gr = GameResult(text=text, intent=intent, metadata=meta)
        if flex:
            if not gr.metadata:
                gr.metadata = {}
            gr.metadata["flex_message"] = flex

        return gr


game_loop = GameLoop()
