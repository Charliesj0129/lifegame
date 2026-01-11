from linebot.v3.messaging import AudioMessage
from app.core.config import settings


class AudioService:
    def get_level_up_audio(self, duration_ms=5000) -> AudioMessage:
        """Returns the Fanfare audio message."""
        url = f"{settings.APP_BASE_URL}/static/audio/levelup.mp3"
        return AudioMessage(original_content_url=url, duration=duration_ms)

    def get_briefing_audio(self, duration_ms=3000) -> AudioMessage:
        """Returns the System Start audio message."""
        url = f"{settings.APP_BASE_URL}/static/audio/briefing.mp3"
        return AudioMessage(original_content_url=url, duration=duration_ms)


audio_service = AudioService()
