from typing import Protocol, TypeVar, Any
from domain.ports.repository import Repository


class UnitOfWork(Protocol):
    """
    Unit of Work Interface.
    Manages transactions and repository access.
    """

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(self, exc_type, exc_value, traceback) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    # In a perfect world, UoW might expose repositories dynamically
    # e.g. uow.users.get(...) through properties.
    # For now, we keep it simple: It manages the SESSION commit.
    # The repositories are instantiated with the session.
