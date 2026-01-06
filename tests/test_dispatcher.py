import pytest
from unittest.mock import AsyncMock
from app.core.dispatcher import CommandDispatcher
from linebot.v3.messaging import TextMessage

@pytest.fixture
def session():
    return AsyncMock()

@pytest.fixture
def dispatcher():
    return CommandDispatcher()

@pytest.mark.asyncio
async def test_exact_match(dispatcher, session):
    # Setup
    handler = AsyncMock(return_value=(TextMessage(text="Pong"), "ping_tool", {}))
    dispatcher.register(lambda t: t == "ping", handler)
    
    # Execute
    msg, tool, data = await dispatcher.dispatch(session, "user1", "ping")
    
    # Assert
    assert msg.text == "Pong"
    assert tool == "ping_tool"
    handler.assert_called_once()

@pytest.mark.asyncio
async def test_fallback(dispatcher, session):
    # Setup
    fallback_handler = AsyncMock(return_value=(TextMessage(text="AI Reply"), "ai_tool", {}))
    dispatcher.register_default(fallback_handler)
    
    # Execute
    msg, tool, data = await dispatcher.dispatch(session, "user1", "hello world")
    
    # Assert
    assert msg.text == "AI Reply"
    assert tool == "ai_tool"
    fallback_handler.assert_called_once()

@pytest.mark.asyncio
async def test_priority(dispatcher, session):
    # Setup
    handler1 = AsyncMock(return_value=("Exact", "exact", {}))
    handler2 = AsyncMock(return_value=("Keyword", "keyword", {}))
    
    dispatcher.register(lambda t: t == "test", handler1)
    dispatcher.register(lambda t: "test" in t, handler2)
    
    # Execute exact match
    res = await dispatcher.dispatch(session, "user", "test")
    assert res[0] == "Exact"
    
    # Execute partial match?
    # Actually register order matters. List is iterated in order.
    # If handler2 registered second, it is second priority?
    # Let's verify standard registration order.
