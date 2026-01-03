import asyncio
from app.services.user_service import user_service
from app.core.database import AsyncSessionLocal
from app.services.ai_engine import ai_engine

# Mock AI engine to avoid hitting API if keys not set, or test real if set
# For safety, let's just inspect the result assuming we have keys or fallback.
# If keys are missing, it falls back. That is fine, fallback has narrative too.

async def test_narrative_flow():
    async with AsyncSessionLocal() as session:
        # Simulate a user action
        result = await user_service.process_action(session, "Utest123", "Run 5km")
        
        print(f"--- Process Result ---")
        print(f"Attribute: {result.attribute}")
        print(f"XP: {result.xp_gained}")
        print(f"Narrative: {result.narrative}")
        print(f"Has Loot: {result.loot_name}")
        
        if result.narrative:
            print("SUCCESS: Narrative field is populated.")
        else:
            print("FAILURE: Narrative field is None.")

if __name__ == "__main__":
    asyncio.run(test_narrative_flow())
