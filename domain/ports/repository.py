from typing import TypeVar, Generic, Optional, List, Protocol, Any

T = TypeVar("T")

class Repository(Protocol[T]):
    """
    Generic Repository Interface.
    Decouples Domain from ORM/SQL usage.
    """
    
    async def get(self, id: Any) -> Optional[T]:
        """Fetch entity by ID."""
        ...
        
    async def add(self, entity: T) -> T:
        """Add new entity."""
        ...
        
    async def save(self, entity: T) -> T:
        """Update existing entity."""
        ...
        
    async def delete(self, id: Any) -> bool:
        """Delete entity by ID."""
        ...
        
    async def list(self, limit: int = 100, offset: int = 0) -> List[T]:
        """List entities."""
        ...
