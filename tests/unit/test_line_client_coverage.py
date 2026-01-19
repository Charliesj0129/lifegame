import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from domain.models.game_result import GameResult
from adapters.perception.line_client import LineClient
from linebot.v3.messaging import TextMessage


@pytest.fixture
def mock_messaging_api():
    with patch("adapters.perception.line_client.get_messaging_api") as mock_get:
        mock_api = MagicMock()
        mock_get.return_value = mock_api
        yield mock_api


@pytest.mark.asyncio
async def test_send_reply_success(mock_messaging_api):
    client = LineClient()
    result = GameResult(text="Hello")

    # Mock Reply success
    mock_messaging_api.reply_message = AsyncMock()

    success = await client.send_reply("token", result)
    assert success is True
    mock_messaging_api.reply_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_reply_failure_raises_exception(mock_messaging_api):
    client = LineClient()
    result = GameResult(text="Hello")

    # Mock Reply failure (400)
    mock_messaging_api.reply_message = AsyncMock(side_effect=Exception("Invalid Token"))

    # Logic change: It should RAISE exception now, not fallback internally
    with pytest.raises(Exception, match="Invalid Token"):
        await client.send_reply("token", result)


@pytest.mark.asyncio
async def test_send_push_rich_success(mock_messaging_api):
    client = LineClient()
    result = GameResult(text="Hello", metadata={"flex_message": {"type": "flex"}})

    mock_messaging_api.push_message = AsyncMock()

    success = await client.send_push("user1", result)
    assert success is True
    # Should call push with flex
    args, _ = mock_messaging_api.push_message.call_args
    assert args[0].to == "user1"


@pytest.mark.asyncio
async def test_send_push_fallback_text(mock_messaging_api):
    client = LineClient()
    result = GameResult(text="Fallback Text", metadata={"flex_message": {"type": "broken_flex"}})

    # First push (Rich) fails
    # Second push (Text) succeeds
    mock_messaging_api.push_message = AsyncMock(side_effect=[Exception("Flex Error"), None])

    success = await client.send_push("user1", result)
    assert success is True

    # Should have been called twice
    assert mock_messaging_api.push_message.call_count == 2

    # Second call should be TextMessage fallback
    args, _ = mock_messaging_api.push_message.call_args_list[1]
    msgs = args[0].messages
    assert len(msgs) == 1
    assert isinstance(msgs[0], TextMessage)
    assert "Display Error" in msgs[0].text
