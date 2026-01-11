from typing import Protocol, Optional, Any
from domain.models.user import User

# Since we haven't moved User model to domain fully yet (it's in app/models),
# we might need a DTO or just use 'Any' temporarily if we want strict separation.
# For Phase 1, we will import the existing User model but acknowledge it's an ORM model.
# Ideally, we should define a pure Domain User and map it.
# But per "No Big Bang", we use the existing User for now or a Protocol.


class PersistencePort(Protocol):
    """
    Interface for data storage (User state, Game state).
    """

    async def get_user(self, user_id: str) -> Optional[Any]:
        """Retrieve user state."""
        ...

    async def save_user(self, user: Any) -> bool:
        """Persist user state."""
        ...

    async def get_quest(self, quest_id: str) -> Optional[Any]:
        """Retrieve quest data."""
        ...
