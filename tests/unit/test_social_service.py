from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.services.social_service import SocialService


@pytest.fixture
def mock_kuzu():
    kuzu = MagicMock()
    kuzu.query = AsyncMock()  # Must be async
    return kuzu


@pytest.fixture
def mock_ai_engine():
    ai = AsyncMock()
    ai.generate_npc_response = AsyncMock(
        return_value={"text": "Hello, mortal.", "intimacy_change": 1, "can_visualize": False}
    )
    return ai


@pytest.fixture
def social_service(mock_kuzu, mock_ai_engine):
    with (
        patch("application.services.social_service.get_kuzu_adapter", return_value=mock_kuzu),
        patch("application.services.social_service.ai_engine", mock_ai_engine),
    ):
        service = SocialService()
        # Re-inject mocks because __init__ might call get_kuzu_adapter immediately
        service.kuzu = mock_kuzu
        yield service


@pytest.mark.asyncio
async def test_interact_flow(social_service, mock_kuzu, mock_ai_engine):
    user_id = "test_user"
    npc_id = "viper"
    text = "Hi Viper!"

    # Act
    response = await social_service.interact(user_id, npc_id, text)

    # Assert
    assert response["text"] == "Hello, mortal."

    # Verify AI called with correct context
    mock_ai_engine.generate_npc_response.assert_called_once()
    call_args = mock_ai_engine.generate_npc_response.call_args
    assert call_args.kwargs["user_input"] == text
    assert call_args.kwargs["persona"]["name"] == "Viper"

    # Verify Graph Update (Relationship)
    mock_kuzu.query.assert_called()
    # Check if cypher query contains MERGE (u)-[r:KNOWS]->(n)
    cypher_call = mock_kuzu.query.call_args[0][0]
    assert "MERGE (u:User {id: '" + user_id + "'})" in cypher_call
    assert "MERGE (n:NPC {id: '" + npc_id + "'})" in cypher_call
    assert "MERGE (u)-[r:KNOWS]->(n)" in cypher_call


@pytest.mark.asyncio
async def test_interact_neutral(social_service, mock_kuzu, mock_ai_engine):
    # Test that delta=0 still updates graph
    mock_ai_engine.generate_npc_response.return_value = {
        "text": "Neutral response.",
        "intimacy_change": 0,
        "can_visualize": False,
    }

    await social_service.interact("u1", "viper", "Hello")

    # Assert execute called even with delta 0
    mock_kuzu.query.assert_called()
    call_args = mock_kuzu.query.call_args
    assert "delta 0" not in str(call_args)  # Delta is merged into cypher query string
    # Just check query structure
    cypher_call = call_args[0][0]
    assert "+ 0" in cypher_call or "intimacy = r.intimacy + 0" in cypher_call
