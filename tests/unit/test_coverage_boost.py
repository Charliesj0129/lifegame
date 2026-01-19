import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from application.services.vector_service import VectorService
from application.services.verification_service import VerificationService, Verdict, VerificationResponse
from application.services.quest_service import QuestService
from app.models.quest import Quest, QuestStatus

# --- Vector Service Tests ---


@pytest.mark.asyncio
async def test_vector_service_add_memory_exception():
    with patch("application.services.vector_service.ChromaAdapter") as mock_adapter_cls:
        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter
        # Simulate Exception
        mock_adapter.add_texts = AsyncMock(side_effect=Exception("DB Down"))

        service = VectorService()
        # Should catch exception and not raise
        await service.add_memory("test")

        mock_adapter.add_texts.assert_called_once()


@pytest.mark.asyncio
async def test_vector_service_search_memories_exception():
    with patch("application.services.vector_service.ChromaAdapter") as mock_adapter_cls:
        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter
        mock_adapter.similarity_search = AsyncMock(side_effect=Exception("DB Down"))

        service = VectorService()
        results = await service.search_memories("query")

        assert results == []


# --- Verification Service Tests ---


@pytest.mark.asyncio
async def test_verification_auto_match_sorting():
    service = VerificationService()
    session = AsyncMock()

    # Mock get_verifiable_quests
    q1 = Quest(id="q1", title="Run", verification_type="TEXT", verification_keywords=["run", "5km"])
    q2 = Quest(id="q2", title="Eat", verification_type="TEXT", verification_keywords=["eat", "food"])

    with patch.object(service, "get_verifiable_quests", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [q1, q2]

        # User implies running
        matched = await service.auto_match_quest(session, "u1", "I ran 5km", "TEXT")
        assert matched == q1

        # User implies eating
        matched_eat = await service.auto_match_quest(session, "u1", "I ate food", "TEXT")
        assert matched_eat == q2


@pytest.mark.asyncio
async def test_verify_image_exception():
    service = VerificationService()
    session = AsyncMock()
    quest = Quest(title="Pic")

    with patch(
        "application.services.verification_service.ai_engine.verify_multimodal", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.side_effect = Exception("AI Error")

        result = await service.verify_image(session, quest, b"data")

        assert result["verdict"] == Verdict.UNCERTAIN
        assert "無法確認" in result["reason"] or "fallback" in result["reason"]


@pytest.mark.asyncio
async def test_verify_location_logic():
    service = VerificationService()
    session = AsyncMock()

    # Target: Taipei 101 approx
    quest = Quest(location_target={"lat": 25.0339, "lng": 121.5644, "radius_m": 100})

    # User at target
    res_hit = await service.verify_location(session, quest, 25.0339, 121.5644)
    assert res_hit["verdict"] == Verdict.APPROVED

    # User far away (+1 degree lat is ~111km)
    res_miss = await service.verify_location(session, quest, 26.0339, 121.5644)
    assert res_miss["verdict"] == Verdict.REJECTED


@pytest.mark.asyncio
async def test_verify_location_invalid():
    service = VerificationService()
    session = AsyncMock()
    quest = Quest(location_target={})  # Empty

    res = await service.verify_location(session, quest, 0, 0)
    assert res["verdict"] == Verdict.UNCERTAIN
    assert "缺少" in res["reason"]


# --- Quest Service Tests ---


@pytest.mark.asyncio
async def test_bulk_adjust_difficulty():
    service = QuestService()
    session = AsyncMock()

    # Mock result with 2 quests
    q1 = Quest(difficulty_tier="S", xp_reward=500, quest_type="SIDE")
    q2 = Quest(difficulty_tier="A", xp_reward=300, quest_type="SIDE")

    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [q1, q2]
    session.execute.return_value = mock_result

    count = await service.bulk_adjust_difficulty(session, "u1", "E")

    assert count == 2
    assert q1.difficulty_tier == "E"
    assert q1.xp_reward == 10
    assert q2.difficulty_tier == "E"
