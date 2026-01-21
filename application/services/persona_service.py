from dataclasses import dataclass
from typing import Optional

from linebot.v3.messaging import Sender


@dataclass
class Persona:
    name: str
    icon_url: Optional[str] = None


class PersonaService:
    """Manages the identity (Name/Icon) of the bot for different contexts."""

    SYSTEM = Persona(
        name="戰術系統",
        icon_url="https://images.unsplash.com/photo-1542831371-29b0f74f9713?q=80&w=200&auto=format&fit=crop",
    )

    VIPER = Persona(
        name="Viper（對手）",
        icon_url="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?q=80&w=200&auto=format&fit=crop",
    )

    MENTOR = Persona(
        name="導師",
        icon_url="https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?q=80&w=200&auto=format&fit=crop",
    )

    def get_sender_object(self, persona: Persona) -> Sender:
        """Returns the Sender object for MessagingApi."""
        return Sender(name=persona.name, iconUrl=persona.icon_url)


persona_service = PersonaService()
