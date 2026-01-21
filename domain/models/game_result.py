from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class QuickReplyAction(BaseModel):
    label: str
    action_data: str  # e.g. "action=buy&id=1"
    display_text: Optional[str] = None


class GameResult(BaseModel):
    """
    Generic result from Application Layer.
    """

    text: str
    image_url: Optional[str] = None
    quick_replies: List[QuickReplyAction] = Field(default_factory=list)

    # Meta info for the system (not shown to user)
    intent: str = "unknown"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Persona Override (Optional)
    persona: Optional[str] = None
