import logging

from app.models.lore import LoreEntry
from application.services.ai_engine import ai_engine

logger = logging.getLogger(__name__)


class NarrativeService:
    async def generate_outcome_story(
        self,
        session,
        user_id: str,
        action_text: str,
        result_data: dict,
        user_context: str = "",
    ) -> str:
        """
        Generates a short, immersive flavor text for an action outcome and saves it as Lore.
        """
        system_prompt = (
            "Role: Cyberpunk RPG Narrator. "
            "Task: Write a 1-sentence action outcome log. "
            "Style: Gritty, Neon, Fast-paced. "
            "Language: ALWAYS use Traditional Chinese (繁體中文). "
            "Output JSON: {'narrative': 'str'}"
        )

        user_prompt = f"Action: {action_text}. Result: {result_data}. Context: {user_context}"

        try:
            data = await ai_engine.generate_json(system_prompt, user_prompt)
            story = data.get("narrative", "Action completed.")

            # Save to Lore
            entry = LoreEntry(series=f"User:{user_id}", chapter=1, title=action_text[:50], body=story)
            session.add(entry)

            return story
        except Exception as e:
            logger.error(f"Narrative Gen Failed: {e}")
            return "Action completed."

    async def get_viper_comment(self, session, user_id: str, context_data: dict | str) -> str:
        """
        Generates a context-aware comment from Viper.
        Args:
            context_data: Dict containing {hp, gold, streak, event, user_level} or legacy str.
        """
        # Fetch Rival
        from application.services.rival_service import rival_service

        rival = await rival_service.get_rival(session, user_id)
        if not rival:
            rival_level = 1
        else:
            rival_level = rival.level

        # Parse Context
        if isinstance(context_data, str):
            # Legacy fallback
            event = context_data
            user_level = 1
            streak = 0
            hp_pct = 100
        else:
            event = context_data.get("event", "General status check")
            user_level = context_data.get("user_level", 1)
            streak = context_data.get("streak", 0)
            hp_pct = context_data.get("hp_pct", 100)

        # Determine Relationship Tier
        level_gap = rival_level - user_level

        if streak > 5 and level_gap < 5:
            relationship = "Respectful Rival"
            tone = "Acknowledging strength, but challenging to do better."
        elif streak == 0 or level_gap > 10:
            relationship = "Hostile/Disappointed"
            tone = "Mocking weakness, arrogant, superior."
        else:
            relationship = "Competitive"
            tone = "Calculated, strictly comparing metrics."

        system_prompt = (
            f"Role: Viper (AI Rival, Lv.{rival_level}). "
            f"Relationship: {relationship}. "
            f"Tone: {tone} "
            "Task: Comment on the user's situation. Max 1 sentence. "
            "Language: ALWAYS use Traditional Chinese (繁體中文). "
            "Output JSON: {'comment': 'str'}"
        )

        user_prompt = f"User Stats: [Lv.{user_level}, HP:{hp_pct}%, Streak:{streak}]. Current Event: {event}."

        try:
            data = await ai_engine.generate_json(system_prompt, user_prompt)
            comment = data.get("comment") or data.get("taunt") or "..."
            return f'🐍 Viper: "{comment}"'
        except Exception:
            return '🐍 Viper: "..."'


narrative_service = NarrativeService()
