import asyncio
import logging
from app.core.database import AsyncSessionLocal
from app.services.goal_decomposer_service import goal_decomposer
from sqlalchemy import select
from app.models.quest import Quest

# Setup Logging
logging.basicConfig(level=logging.INFO)

async def test_decomposition():
    print("\n--- Testing Goal Decomposition (Gemini 3 Flash) ---")
    user_id = "U_TEST_VIPER"
    goal_input = "I want to become a Python Backend Expert in 3 months"
    
    async with AsyncSessionLocal() as session:
        print(f"Input Goal: {goal_input}")
        
        goal = await goal_decomposer.decompose_and_save(session, user_id, goal_input)
        
        if goal:
            print(f"\n✅ Goal Created: {goal.title}")
            print(f"📜 Narrative: {goal.description}")
            
            # Fetch Quests
            result = await session.execute(select(Quest).where(Quest.goal_id == goal.id))
            quests = result.scalars().all()
            
            print(f"\n🔻 Generated Quests ({len(quests)}):")
            for q in quests:
                print(f"   - [{q.status}] {q.title} (Diff: {q.difficulty_tier} | XP: {q.xp_reward})")
                
            if len(quests) >= 3:
                print("\n✅ Sub-Quest Count Valid.")
            else:
                print("\n❌ Too few quests generated.")
                
        else:
            print("\n❌ Goal Decomposition Failed (Returns None).")

if __name__ == "__main__":
    asyncio.run(test_decomposition())
