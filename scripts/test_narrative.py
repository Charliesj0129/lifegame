import asyncio
from app.services.user_service import user_service
from app.core.database import AsyncSessionLocal
from app.services.ai_engine import ai_engine

# Mock AI engine to avoid hitting API if keys not set, or test real if set
# For safety, let's just inspect the result assuming we have keys or fallback.
# If keys are missing, it falls back. That is fine, fallback has narrative too.

async def test_narrative_flow():
    async with AsyncSessionLocal() as session:
        import time
        
        # Test 1: Fast Mode (Short Keyword)
        t0 = time.time()
        res_fast = await user_service.process_action(session, "Utest123", "Gym")
        t_fast = (time.time() - t0) * 1000
        print(f"\n[FAST MODE] Input: 'Gym' | Time: {t_fast:.2f}ms")
        print(f"Narrative: {res_fast.narrative}")
        print(f"Loot: {res_fast.loot_name} (Should be None for Fast Mode usually)")
        print(f"Streak: {res_fast.streak_count}")
        
        if "System 1" in res_fast.narrative:
            print("✅ Fast Mode Triggered")
        else:
            print("❌ Fast Mode FAILED")

        # Test 2: Slow Mode (Long Context)
        t0 = time.time()
        res_slow = await user_service.process_action(session, "Utest123", "I ran a marathon in the rain and felt amazing")
        t_slow = (time.time() - t0) * 1000
        print(f"\n[SLOW MODE] Input: 'Marathon...' | Time: {t_slow:.2f}ms")
        print(f"Narrative: {res_slow.narrative}")
        
        if "System 1" not in res_slow.narrative:
             print("✅ Slow Mode Triggered (AI Content)")
        else:
             print("❌ Slow Mode FAILED (Got Fast Response)")

if __name__ == "__main__":
    asyncio.run(test_narrative_flow())
