import google.generativeai as genai
from openai import AsyncOpenAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        self.client = None
        self.model = None
        self.provider = "none"
        self.rules_context = ""

        # Load Rules of the World & Minify
        try:
            with open("doc/rules_of_the_world.md", "r", encoding="utf-8") as f:
                raw_rules = f.read()
                self.rules_context = self._minify_rules(raw_rules)
        except Exception:
            self.rules_context = "Rules file not found."

        if settings.OPENROUTER_API_KEY:
            self.client = AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                timeout=15.0
            )
            self.model = settings.OPENROUTER_MODEL
            self.provider = "openrouter"
            logger.info(f"AI Engine initialized with OpenRouter ({self.model})")
        elif settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
            self.provider = "google"
            logger.info(f"AI Engine initialized with Google Gemini ({self.model.model_name})")
        else:
            logger.warning("No AI API Keys set. AI Engine disabled.")

    def _minify_rules(self, text: str) -> str:
        """Strip markdown and extra whitespace to save tokens."""
        import re
        text = re.sub(r'#+\s*', '', text) # Remove headers
        text = re.sub(r'\n+', ' ', text)  # Collapse newlines
        text = re.sub(r'\s+', ' ', text)  # Collapse spaces
        return text.strip()[:2000] # Cap length just in case

    async def analyze_action(self, user_text: str) -> dict:
        import time
        start_time = time.time()
        
        if self.provider == "none":
            return {
                "narrative": "⚠️ 神經連結離線。執行本地模擬程序。",
                "xp_gained": 10,
                "stat_type": "VIT",
                "loot_drop": {"has_loot": False},
                "feedback_tone": "WARNING",
                "difficulty_tier": "F" 
            }

        # Optimized "One-Shot" Prompt
        system_prompt = f"""Role: Cyberpunk LifeOS (Beta v.2077) - 繁體中文版.
Task: Analyze User Action -> Calculate Stats -> Feedback.
Rules: {self.rules_context}
Constraint: OUTPUT TRADITIONAL CHINESE ONLY. JSON ONLY.
Output Schema:
{{
  "narrative": "Story output < 50 chars",
  "difficulty_tier": "E"|"D"|"C"|"B"|"A",
  "stat_type": "STR"|"INT"|"VIT"|"WIS"|"CHA",
  "loot_drop": {{ "has_loot": bool, "item_name": "str", "description": "str" }},
  "feedback_tone": "ENCOURAGING"|"SARCASTIC"|"WARNING"
}}"""
        
        user_prompt = f"Action: {user_text}"

        try:
            content = ""
            if self.provider == "openrouter":
                completion = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                content = completion.choices[0].message.content
            
            elif self.provider == "google":
                full_prompt = system_prompt + " " + user_prompt
                response = await self.model.generate_content_async(full_prompt)
                content = response.text

            # Latency Log
            elapsed = (time.time() - start_time) * 1000
            print(f"AI_LATENCY_MS: {elapsed:.2f}ms | Model: {self.model}")

            import json
            if "```json" in content:
                content = content.replace("```json", "").replace("```", "")
            elif "```" in content:
                content = content.replace("```", "")
            
            return json.loads(content)

        except Exception as e:
            logger.error(f"AI Analysis Failed: {e}", exc_info=True)
            return {
                "narrative": "⚠️ 訊號丟失。手動覆蓋模式已啟動。",
                "difficulty_tier": "E",
                "stat_type": "VIT",
                "loot_drop": {"has_loot": False},
                "feedback_tone": "WARNING"
            }

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        """
        Generic method to generate JSON from AI.
        Supports both OpenRouter (Native JSON) and Google (Markdown parsing).
        """
        import json
        import time
        start = time.time()
        
        try:
            content = ""
            if self.provider == "openrouter":
                completion = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                content = completion.choices[0].message.content
            
            elif self.provider == "google":
                # Force JSON in prompt for legacy Google models
                full_prompt = f"{system_prompt}\n\nUSER INPUT: {user_prompt}\n\nIMPORTANT: OUTPUT JSON ONLY."
                response = await self.model.generate_content_async(full_prompt)
                content = response.text
            else:
                 return {"error": "AI_OFFLINE"}

            elapsed = (time.time() - start) * 1000
            print(f"AI_GEN_LATENCY: {elapsed:.2f}ms | {self.model}")
            
            # Clean Markdown
            if "```json" in content:
                content = content.replace("```json", "").replace("```", "")
            elif "```" in content:
                content = content.replace("```", "")
            
            return json.loads(content)

        except Exception as e:
            logger.error(f"AI JSON Gen Failed: {e}")
            return {"error": str(e)}

# Global instance
ai_engine = AIEngine()
