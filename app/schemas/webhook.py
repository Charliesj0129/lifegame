from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class HAEventPayload(BaseModel):
    event_type: str = Field(..., description="The type of event (e.g., 'screen_on', 'location_update')")
    entity_id: Optional[str] = Field(None, description="The specific entity involved")
    state: Optional[str] = Field(None, description="The new state")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Extra data from HA")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")
