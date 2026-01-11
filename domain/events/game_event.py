from deepdiff import DeepHash
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class GameEvent(BaseModel):
    """
    Universal Event Model for LifeGame.
    Decouples the source (LINE, HA, Tasker) from the Domain Logic.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str  # "line", "ha", "cron", "manual"
    source_id: str # user_id from LINE, or device_id from HA
    
    type: str # "message", "screen_on", "location_update"
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Payload abstraction
    text: Optional[str] = None
    image_data: Optional[bytes] = None
    location: Optional[tuple[float, float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        """Generate a hash for idempotency checks."""
        # We hash the essential content, ignoring ID and timestamp if close enough
        return DeepHash(self.dict(include={'source', 'source_id', 'type', 'text', 'metadata'})).get(self)
