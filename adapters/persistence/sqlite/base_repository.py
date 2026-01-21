from typing import Any, List, Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.ports.repository import Repository, T


class SqlAlchemyRepository(Repository[T]):
    def __init__(self, session: AsyncSession, model_cls: Type[T]):
        self.session = session
        self.model_cls = model_cls

    async def get(self, id: Any) -> Optional[T]:
        return await self.session.get(self.model_cls, id)

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        return entity

    async def save(self, entity: T) -> T:
        await self.session.merge(entity)
        return entity

    async def delete(self, id: Any) -> bool:
        obj = await self.get(id)
        if obj:
            await self.session.delete(obj)
            return True
        return False

    async def list(self, limit: int = 100, offset: int = 0) -> List[T]:
        stmt = select(self.model_cls).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
