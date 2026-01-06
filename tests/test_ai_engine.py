import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.ai_engine import AIEngine


def test_minify_rules():
    engine = AIEngine()
    raw = "# Title\n\nLine1\n\nLine2"
    result = engine._minify_rules(raw)
    assert "Title Line1 Line2" in result
    assert "\n" not in result


def test_strip_code_fences():
    engine = AIEngine()
    content = "```json\n{\"a\": 1}\n```"
    cleaned = engine._strip_code_fences(content)
    assert cleaned == "{\"a\": 1}"


def test_extract_json_block():
    engine = AIEngine()
    content = "prefix {\"a\": 1} suffix"
    extracted = engine._extract_json_block(content)
    assert extracted == "{\"a\": 1}"


def test_safe_json_load_invalid():
    engine = AIEngine()
    assert engine._safe_json_load("{bad") is None


@pytest.mark.asyncio
async def test_generate_json_parses_codefence():
    engine = AIEngine()
    engine.provider = "google"

    response = MagicMock()
    response.text = "```json\n{\"foo\": 1}\n```"
    engine.model = MagicMock()
    engine.model.generate_content_async = AsyncMock(return_value=response)

    result = await engine.generate_json("sys", "user")
    assert result["foo"] == 1


@pytest.mark.asyncio
async def test_generate_json_repair_flow():
    engine = AIEngine()
    engine.provider = "google"

    bad = MagicMock()
    bad.text = "not json at all"
    fixed = MagicMock()
    fixed.text = "{\"bar\": 2}"

    engine.model = MagicMock()
    engine.model.generate_content_async = AsyncMock(side_effect=[bad, fixed])

    result = await engine.generate_json("sys", "user")
    assert result["bar"] == 2
    assert engine.model.generate_content_async.call_count == 2


@pytest.mark.asyncio
async def test_verify_multimodal_offline():
    engine = AIEngine()
    engine.provider = "none"

    result = await engine.verify_multimodal(
        mode="TEXT", quest_title="Quest", user_text="done"
    )
    assert result["verdict"] == "UNCERTAIN"
    assert "離線" in result["reason"]


@pytest.mark.asyncio
async def test_analyze_action_offline():
    engine = AIEngine()
    engine.provider = "none"

    result = await engine.analyze_action("drink water")
    assert result["difficulty_tier"] == "F"
    assert "神經連結離線" in result["narrative"]
