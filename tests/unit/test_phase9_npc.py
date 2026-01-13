import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from legacy.services.npc_service import npc_service


@pytest.mark.asyncio
async def test_npc_profiles():
    # 1. Test Kael (Merchant)
    with patch("legacy.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = {"dialogue": "Price goes up tomorrow."}

        ctx = {"item_bought": "Potion", "cost": 50, "user_gold_left": 10}
        dialogue = await npc_service.get_dialogue("kael", "User bought Potion.", ctx)

        assert "Kael" in dialogue
        assert "Price goes up" in dialogue

        # Verify Prompt contains traits
        args, _ = mock_ai.call_args
        prompt = args[0]
        assert "Greedy" in prompt
        assert "Kael" in prompt

    # 2. Test Aria (Mentor)
    with patch("legacy.services.ai_engine.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = {"dialogue": "Discipline is freedom."}

        dialogue = await npc_service.get_dialogue("aria", "User reached streak 10.")

        assert "Aria" in dialogue

        args, _ = mock_ai.call_args
        prompt = args[0]
        assert "Stoic" in prompt

    # 3. Test System (Fast path, no AI)
    dialogue = await npc_service.get_dialogue("system", "Operation complete.")
    assert "[LifeOS]" in dialogue
    assert "Operation complete" in dialogue
