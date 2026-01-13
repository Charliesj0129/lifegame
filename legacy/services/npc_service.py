from legacy.services.ai_engine import ai_engine
import logging

logger = logging.getLogger(__name__)


class NPCService:
    PROFILES = {
        "kael": {
            "name": "Kael",
            "role": "Black Market Merchant",
            "traits": "Greedy, Cynical, Observant",
            "tone": "Sarcastic, focused on profit, but respects big spenders.",
            "prompt": "You are Kael, a black market dealer in a cyberpunk slum. You sell illegal enhancements. You care only about credits.",
        },
        "aria": {
            "name": "Aria",
            "role": "Resistance Mentor",
            "traits": "Stoic, Disciplined, Inspiring",
            "tone": "Calm, firm, military-like precision.",
            "prompt": "You are Aria, a former corporate soldier turned resistance trainer. You value discipline and strength above all.",
        },
        "system": {
            "name": "LifeOS",
            "role": "System AI",
            "traits": "Robotic, Neutral, Efficient",
            "tone": "Monotone, informative.",
            "prompt": "You are LifeOS, the system interface. You have no personality.",
        },
    }

    async def get_dialogue(self, npc_key: str, context: str, user_context: dict = None) -> str:
        """
        Generates dialogue for a specific NPC.
        """
        profile = self.PROFILES.get(npc_key.lower())
        if not profile:
            return "..."

        if npc_key == "system":
            # Fast path for system
            return f"[{profile['name']}] {context}"

        system_prompt = (
            f"Role: {profile['name']} ({profile['role']}). "
            f"Personality: {profile['traits']}. Tone: {profile['tone']} "
            f"Base Prompt: {profile['prompt']} "
            "Language: ALWAYS use Traditional Chinese (繁體中文). "
            "Task: Generate a 1-sentence response to the user's action. "
            "Output JSON: {'dialogue': 'str'}"
        )

        user_prompt = f"Action/Context: {context}."
        if user_context:
            user_prompt += f" User State: {user_context}."

        try:
            data = await ai_engine.generate_json(system_prompt, user_prompt)
            dialogue = data.get("dialogue") or "..."
            return f"👤 {profile['name']}: 「{dialogue}」"
        except Exception:
            return f"👤 {profile['name']}: 「...」"


npc_service = NPCService()
