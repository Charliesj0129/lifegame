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

    def _strip_code_fences(self, content: str) -> str:
        if not content:
            return content
        cleaned = content.replace("```json", "").replace("```", "")
        return cleaned.strip()

    def _extract_json_block(self, content: str) -> str | None:
        if not content:
            return None
        start_candidates = [content.find("{"), content.find("[")]
        start_candidates = [idx for idx in start_candidates if idx != -1]
        if not start_candidates:
            return None
        start = min(start_candidates)
        end = max(content.rfind("}"), content.rfind("]"))
        if end == -1 or end <= start:
            return None
        return content[start:end + 1]

    def _safe_json_load(self, content: str) -> dict | list | None:
        import json
        try:
            return json.loads(content)
        except Exception:
            return None

    def _log_latency(self, event: str, elapsed_ms: float) -> None:
        if not settings.ENABLE_LATENCY_LOGS:
            return
        logger.debug("event=%s duration_ms=%.2f model=%s", event, elapsed_ms, self.model)

    async def analyze_action(self, user_text: str) -> dict:
        import time
        start_time = time.time() if settings.ENABLE_LATENCY_LOGS else None
        
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

            if start_time is not None:
                elapsed = (time.time() - start_time) * 1000
                self._log_latency("ai_request_latency", elapsed)

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

    async def analyze_image(self, image_bytes: bytes, mime_type: str, prompt: str) -> dict:
        """
        Analyzes an image using Vision Model (Gemini).
        Returns JSON verification result.
        """
        import time
        start = time.time() if settings.ENABLE_LATENCY_LOGS else None
        
        system_prompt = (
            "Role: Verification AI (The Arbiter). "
            "Task: Verify if the image matches the User's Quest Requirement. "
            "Language: ALWAYS use Traditional Chinese (繁體中文). "
            "Output JSON: { 'verdict': 'APPROVED'|'REJECTED'|'UNCERTAIN', 'reason': 'str', 'tags': ['str'] }"
        )
        
        try:
            content = ""
            if self.provider == "google":
                # Gemini Pro Vision / Flash support byte data
                image_part = {
                    "mime_type": mime_type,
                    "data": image_bytes
                }
                
                full_prompt = [system_prompt, f"Quest Requirement: {prompt}", image_part]
                
                # Note: Some older gemini libs expect 'parts' list differently.
                # But generate_content_async usually accepts a list of [text, image].
                response = await self.model.generate_content_async(full_prompt)
                content = response.text
                
            elif self.provider == "openrouter":
                # OpenRouter Vision support varies. 
                # Assuming simple GPT-4o style if available, but usually requires URL or base64.
                # For MVP if OpenRouter is used, might fall back or skip.
                # Let's assume we skip or just fail for now if not Google.
                import base64
                b64 = base64.b64encode(image_bytes).decode('utf-8')
                
                completion = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": [
                            {"type": "text", "text": f"Requirement: {prompt}"},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}}
                        ]}
                    ],
                    response_format={"type": "json_object"}
                )
                content = completion.choices[0].message.content
                
            if start is not None:
                elapsed = (time.time() - start) * 1000
                self._log_latency("ai_vision_latency", elapsed)
            
            # Clean JSON
            if "```json" in content:
                content = content.replace("```json", "").replace("```", "")
            elif "```" in content:
                content = content.replace("```", "")
            
            import json
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Image Analysis Failed: {e}")
            return {"verdict": "UNCERTAIN", "reason": f"Vision AI Error: {str(e)}", "tags": []}

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        """
        Generic method to generate JSON from AI.
        Supports both OpenRouter (Native JSON) and Google (Markdown parsing).
        """
        import time
        start = time.time() if settings.ENABLE_LATENCY_LOGS else None
        
        try:
            async def _call_model(prompt_system: str, prompt_user: str) -> str:
                if self.provider == "openrouter":
                    completion = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": prompt_system},
                            {"role": "user", "content": prompt_user}
                        ],
                        response_format={"type": "json_object"}
                    )
                    return completion.choices[0].message.content

                if self.provider == "google":
                    full_prompt = f"{prompt_system}\n\nUSER INPUT: {prompt_user}\n\nIMPORTANT: OUTPUT JSON ONLY."
                    response = await self.model.generate_content_async(full_prompt)
                    return response.text

                return ""

            if self.provider == "none":
                return {"error": "AI_OFFLINE"}

            content = await _call_model(system_prompt, user_prompt)

            if start is not None:
                elapsed = (time.time() - start) * 1000
                self._log_latency("ai_json_latency", elapsed)
            
            cleaned = self._strip_code_fences(content)
            parsed = self._safe_json_load(cleaned)
            if parsed is not None:
                return parsed

            extracted = self._extract_json_block(cleaned)
            if extracted:
                parsed = self._safe_json_load(extracted)
                if parsed is not None:
                    return parsed

            repair_system = "你是 JSON 修復器，只能輸出有效 JSON。"
            repair_user = f"以下內容無法解析為 JSON，請修正後只輸出 JSON：\n{cleaned}"
            repair_content = await _call_model(repair_system, repair_user)
            repair_cleaned = self._strip_code_fences(repair_content)
            parsed = self._safe_json_load(repair_cleaned)
            if parsed is not None:
                return parsed

            extracted = self._extract_json_block(repair_cleaned)
            if extracted:
                parsed = self._safe_json_load(extracted)
                if parsed is not None:
                    return parsed

            return {"error": "JSON_PARSE_FAILED"}

        except Exception as e:
            logger.error(f"AI JSON Gen Failed: {e}")
            return {"error": str(e)}

    async def verify_multimodal(
        self,
        mode: str,
        quest_title: str,
        user_text: str | None = None,
        image_bytes: bytes | None = None,
        mime_type: str | None = None,
        keywords: list[str] | None = None,
    ) -> dict:
        mode = (mode or "TEXT").upper()
        keywords = keywords or []

        if self.provider == "none":
            return {
                "verdict": "UNCERTAIN",
                "reason": "AI 離線，無法判定。",
                "detected_labels": [],
            }

        if mode == "TEXT":
            system_prompt = (
                "Role: Quest Arbiter. "
                "Task: Determine if the report proves the quest completion. "
                "If vague, return UNCERTAIN with a follow_up question. "
                "Language: ALWAYS use Traditional Chinese (繁體中文). "
                "Output JSON: { 'verdict': 'APPROVED'|'REJECTED'|'UNCERTAIN', "
                "'reason': 'str', 'follow_up': 'str|null', 'detected_labels': ['str'] }"
            )
            user_prompt = (
                f"Quest: {quest_title}\n"
                f"Keywords: {', '.join(keywords)}\n"
                f"User Report: {user_text or ''}"
            )
            return await self.generate_json(system_prompt, user_prompt)

        if mode == "IMAGE":
            system_prompt = (
                "Role: Vision Arbiter. "
                "Task: Check if the image matches the Quest Requirement. "
                "Language: ALWAYS use Traditional Chinese (繁體中文). "
                "Output JSON: { 'verdict': 'APPROVED'|'REJECTED'|'UNCERTAIN', "
                "'reason': 'str', 'detected_labels': ['str'] }"
            )
            user_prompt = f"Quest: {quest_title}\nKeywords: {', '.join(keywords)}"

            # Google Gemini supports image input
            if self.provider == "google" and image_bytes:
                try:
                    response = await self.model.generate_content_async(
                        [system_prompt + "\n" + user_prompt, {"mime_type": mime_type or "image/jpeg", "data": image_bytes}]
                    )
                    content = response.text
                    if "```json" in content:
                        content = content.replace("```json", "").replace("```", "")
                    elif "```" in content:
                        content = content.replace("```", "")
                    import json
                    return json.loads(content)
                except Exception as e:
                    logger.error(f"Vision verification failed: {e}")
                    return {
                        "verdict": "UNCERTAIN",
                        "reason": "無法解析圖片內容。",
                        "detected_labels": [],
                    }

            # Fallback: no vision
            return {
                "verdict": "UNCERTAIN",
                "reason": "目前未啟用圖片辨識。",
                "detected_labels": [],
            }

        return {
            "verdict": "UNCERTAIN",
            "reason": "未知的驗證模式。",
            "detected_labels": [],
        }


# Global instance
ai_engine = AIEngine()
