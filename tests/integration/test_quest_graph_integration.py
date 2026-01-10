import pytest
import os
import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy import select
from legacy.models.quest import Quest, QuestStatus
from legacy.services.quest_service import quest_service
from adapters.persistence.kuzu.adapter import KuzuAdapter
from application.services.graph_service import graph_service

# Separate Test DB for integration
TEST_GRAPH_DB = "./test_kuzu_integration_db"

@pytest.fixture
def test_graph_adapter():
    def cleanup():
        if os.path.exists(TEST_GRAPH_DB):
            import shutil
            if os.path.isdir(TEST_GRAPH_DB):
                shutil.rmtree(TEST_GRAPH_DB)
            else:
                os.remove(TEST_GRAPH_DB)
    cleanup()
    
    adapter = KuzuAdapter(db_path=TEST_GRAPH_DB)
    yield adapter
    
    # Force close before cleanup?
    # Kuzu connection might hold lock.
    # In python, usually garbage collection or just del helps.
    del adapter
    cleanup()

@pytest.mark.asyncio
async def test_quest_graph_cycle(db_session, test_graph_adapter):
    """
    Test full cycle:
    1. Graph: Setup Chain A -> B.
    2. QuestService: Generate Daily (Should get A).
    3. QuestService: Complete A.
    4. Graph: Verify A completed.
    5. QuestService: Generate Daily (Should get B).
    """
    user_id = "test_user_int"
    
    # --- 1. Setup Graph ---
    # Inject adapter into singleton
    graph_service._adapter = test_graph_adapter
    
    # Create User in Graph
    test_graph_adapter.add_node("User", {"id": user_id, "name": user_id})
    
    # Create Chain: Q_A -> Q_B
    test_graph_adapter.add_node("Quest", {"id": "Q_A", "title": "Quest A"})
    test_graph_adapter.add_node("Quest", {"id": "Q_B", "title": "Quest B"})
    test_graph_adapter.add_quest_dependency("Q_B", "Q_A")
    
    # --- 2. Generate Daily (Expect Q_A) ---
    # We mock AI engine to return empty or generic to avoid calling LLM
    # QuestService will try to inject Graph Quest if count >= 2.
    # So we need AI to return at least 1-2 generic quests or we mock the response.
    
    with patch("legacy.services.quest_service.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
        # AI returns 1 generic quest
        mock_ai.return_value = [{"title": "Generic Task", "desc": "Do things", "diff": "D", "xp": 10}]
        
        # We need time_context="Daily" which defaults count to 3.
        # This allows injection (count >= 2).
        
        generated = await quest_service._generate_daily_batch(db_session, user_id, time_context="Daily")
        
        # Verify we got Q_A
        # generated list should contain Q_A
        titles = [q.title for q in generated]
        # Our injection adds brackets: "【Quest A】"
        assert any("Quest A" in t for t in titles), f"Quest A not found in {titles}"
        
        # Find the SQL Quest object for A
        quest_a_sql = next(q for q in generated if "Quest A" in q.title)
        assert quest_a_sql.meta["graph_node_id"] == "Q_A"
        
        # Verify B is NOT relevant yet
        assert not any("Quest B" in t for t in titles)

    # --- 3. Complete A ---
    # Mock LootService to be simple (it calls random)
    # Actually real LootService is fine, logic is deterministic enough for structure.
    # But we need to ensure User exists in SQL if QuestService completion accesses it.
    # user_service.get_user needs to work.
    
    # Create User in SQL
    # Create User in SQL
    from app.models.user import User
    sql_user = User(id=user_id, name="Tester", level=1, xp=0)
    db_session.add(sql_user)
    await db_session.commit()
    
    # Complete
    res = await quest_service.complete_quest(db_session, user_id, quest_a_sql.id)
    assert res is not None
    assert "loot" in res
    assert "quest" in res
    assert res["loot"].xp >= 0
    
    # --- 4. Verify Graph Completion ---
    # Check relationship (User)-[:COMPLETED]->(Q_A)
    # Query graph
    check_query = (
        f"MATCH (u:User {{name: '{user_id}'}})-[:COMPLETED]->(q:Quest {{id: 'Q_A'}}) "
        f"RETURN q.id"
    )
    graph_res = test_graph_adapter.query(check_query)
    assert len(graph_res) > 0, "Graph completion relationship missing!"

    # --- 5. Generate Daily Again (Expect Q_B) ---
    # Need to simulate next day? Or just call generate again.
    # get_daily_quests checks if quests exist for today.
    # If we call _generate_daily_batch directly, it ignores existing check (it just gens).
    # We will call _generate directly.
    
    with patch("legacy.services.quest_service.ai_engine.generate_json", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = [{"title": "Generic Task 2", "desc": "Do things", "diff": "D", "xp": 10}]
        
        generated_2 = await quest_service._generate_daily_batch(db_session, user_id, time_context="Daily")
        
        titles_2 = [q.title for q in generated_2]
        # Should have Q_B now
        assert any("Quest B" in t for t in titles_2), f"Quest B not found in {titles_2}"
        assert not any("Quest A" in t for t in titles_2) # A is done, so not unlockable (filtered out)

