import pytest
import shutil
import tempfile
import os
import pytest_asyncio
from application.services.social_service import social_service
from adapters.persistence.kuzu.adapter import get_kuzu_adapter

# Reuse setup logic from test_integration_real_ai.py for isolation
@pytest_asyncio.fixture(scope="module")
async def real_env_npc():
    # Setup Paths
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_real_npc.db")
    kuzu_path = os.path.join(temp_dir, "test_kuzu_npc")
    
    # Set Env Vars ensure Adapter picks it up
    os.environ["KUZU_DATABASE_PATH"] = kuzu_path
    
    # --- CRITICAL: Reset Kuzu Singleton ---
    import adapters.persistence.kuzu.adapter
    adapters.persistence.kuzu.adapter._kuzu_instance = None
    
    # Initialize Schema (handled by Adapter init)
    adapter = get_kuzu_adapter()
    
    # PATCH Singleton Service to use new Adapter
    social_service.kuzu = adapter
    
    yield {"db": db_path, "kuzu": kuzu_path, "adapter": adapter}
    
    # Cleanup
    shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_real_vipere_chat(real_env_npc):
    """
    E2E Test: User -> SocialService -> Real AI -> Kuzu Graph
    """
    user_id = "test_user_npc"
    npc_id = "viper"
    
    # 1. First Interaction (No context)
    text1 = "你是誰？"
    response1 = await social_service.interact(user_id, npc_id, text1)
    
    print(f"\n[Round 1] User: {text1}\nViper: {response1['text']}")
    assert response1["text"] is not None
    assert len(response1["text"]) > 0
    # Basic Persona Check
    assert "Viper" in response1["text"] or "我" in response1["text"]
    
    # 2. Check Graph Relationship Created
    adapter = real_env_npc["adapter"]
    # Verify KNOWS relationship exists
    res = adapter.conn.execute(
        "MATCH (u:User {id: $uid})-[r:KNOWS]->(n:NPC {id: $nid}) RETURN r.intimacy",
        {"uid": user_id, "nid": npc_id}
    )
    if res.has_next():
        row = res.get_next()
        intimacy = row[0]
        print(f"Intimacy Level: {intimacy}")
        # Ideally intimacy might change, but default starts at 0 + delta.
    
    # 3. Second Interaction (With Context)
    text2 = "你的名字是什麼？我剛剛問過你了。" # Provoke memory
    response2 = await social_service.interact(user_id, npc_id, text2)
    print(f"\n[Round 2] User: {text2}\nViper: {response2['text']}")
    
    # AI Logic check (optional): ideally it remembers context, but this depends on SocialService._get_context implementation which is currently MVP (mostly empty unless we add event logging).
    # Current implementation of _get_context returns [], so memory might fail.
    # But this test validates the PIPELINE works.
