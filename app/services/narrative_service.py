from app.services.ai_engine import ai_engine
from app.models.lore import LoreEntry
import logging

logger = logging.getLogger(__name__)

class NarrativeService:
    async def generate_outcome_story(self, session, user_id: str, action_text: str, result_data: dict, user_context: str = "") -> str:
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
            entry = LoreEntry(
                series=f"User:{user_id}",
                chapter=1,
                title=action_text[:50],
                body=story
            )
            session.add(entry)
            
            return story
        except Exception as e:
            logger.error(f"Narrative Gen Failed: {e}")
            return "Action completed."

    async def get_viper_comment(self, session, user_id: str, context: str) -> str:
        """
        Generates a taunt or comment from the Rival (Viper).
        """
        # Fetch Rival Level
        from app.services.rival_service import rival_service
        rival = await rival_service.get_rival(session, user_id)
        if not rival:
            return "..."
            
        system_prompt = (
            f"Role: Viper (Rival AI, Lv.{rival.level}). "
            "Personality: Arrogant, Calculating, but pushes the user to be better. "
            "Task: Comment on the user's situation. Max 1 sentence. "
            "Language: ALWAYS use Traditional Chinese (繁體中文). "
            "Output JSON: {'comment': 'str'}"
        )
        
        try:
            data = await ai_engine.generate_json(system_prompt, f"Context: {context}")
            return f"🐍 Viper: \"{data.get('comment', 'Pathetic.')}\""
        except Exception:
            return "🐍 Viper: \"...\""

narrative_service = NarrativeService()
