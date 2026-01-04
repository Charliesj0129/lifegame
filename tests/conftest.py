import pytest
import pytest_asyncio
import aiosqlite.core as aiosqlite_core
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
# Import all models to ensure metadata is populated
from app.models.user import User
from app.models.gamification import Item, UserItem, UserBuff
from app.models.action_log import ActionLog

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async def _connect_direct(self):
    if self._connection is None:
        self._connection = self._connector()
    return self

def _await_direct(self):
    return _connect_direct(self).__await__()

async def _execute_direct(self, fn, *args, **kwargs):
    if not self._connection:
        raise ValueError("Connection closed")
    return fn(*args, **kwargs)

async def _close_direct(self):
    if self._connection is None:
        return
    self._connection.close()
    self._connection = None
    self._running = False

def _stop_direct(self):
    self._running = False
    if self._connection is not None:
        self._connection.close()
        self._connection = None
    return None

aiosqlite_core.Connection._connect = _connect_direct
aiosqlite_core.Connection.__await__ = _await_direct
aiosqlite_core.Connection._execute = _execute_direct
aiosqlite_core.Connection.close = _close_direct
aiosqlite_core.Connection.stop = _stop_direct

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    
    await engine.dispose()
