import hashlib
import logging
import os

from linebot.v3.messaging import AudioMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


class AudioService:
    def get_level_up_audio(self, duration_ms=5000) -> AudioMessage:
        """Returns the Fanfare audio message."""
        url = f"{settings.APP_BASE_URL}/static/audio/levelup.mp3"
        return AudioMessage(original_content_url=url, duration=duration_ms)

    def get_briefing_audio(self, duration_ms=3000) -> AudioMessage:
        """Returns the System Start audio message."""
        url = f"{settings.APP_BASE_URL}/static/audio/briefing.mp3"
        return AudioMessage(original_content_url=url, duration=duration_ms)

    async def generate_briefing_audio(self, text: str, duration_ms: int = 15000) -> AudioMessage | None:
        """
        Generates a personalized voice briefing using TTS.
        Falls back to static audio if TTS is unavailable.
        """
        try:
            import httpx

            api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.warning("No API key for TTS; falling back to static briefing.")
                return self.get_briefing_audio(duration_ms)

            # Generate a unique filename based on text hash
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            audio_path = f"./data/audio/briefing_{text_hash}.mp3"
            audio_url = f"{settings.APP_BASE_URL}/static/audio/briefing_{text_hash}.mp3"

            # Check if already generated
            if os.path.exists(audio_path):
                return AudioMessage(original_content_url=audio_url, duration=duration_ms)

            # Ensure directory exists
            os.makedirs("./data/audio", exist_ok=True)

            # Call OpenAI TTS API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "tts-1",
                        "voice": "alloy",
                        "input": text[:1000],  # Limit to 1000 chars
                    },
                    timeout=30.0,
                )
                if response.status_code == 200:
                    with open(audio_path, "wb") as f:
                        f.write(response.content)
                    logger.info(f"Generated TTS audio: {audio_path}")
                    return AudioMessage(original_content_url=audio_url, duration=duration_ms)
                else:
                    logger.error(f"TTS API failed: {response.status_code} - {response.text}")
                    return self.get_briefing_audio(duration_ms)

        except Exception as e:
            logger.error(f"TTS generation failed: {e}", exc_info=True)
            return self.get_briefing_audio(duration_ms)


audio_service = AudioService()
