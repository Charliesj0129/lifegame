import pytest
import shutil
from adapters.persistence.kuzu.adapter import KuzuAdapter

QUERY_PATH = "./test_kuzu_db"

@pytest.fixture
def adapter():
    # Setup
    import os
    import importlib.util
    spec = importlib.util.spec_from_file_location("adapters.persistence.kuzu.adapter", "/home/charlie/lifgame/adapters/persistence/kuzu/adapter.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    KuzuAdapter = module.KuzuAdapter

    if os.path.exists(QUERY_PATH):
        if os.path.isdir(QUERY_PATH):
            shutil.rmtree(QUERY_PATH)
        else:
            os.remove(QUERY_PATH)
            # Try removing aux files
            try:
                os.remove(QUERY_PATH + ".wal")
            except Exception:
                pass
    
    adapter = KuzuAdapter(db_path=QUERY_PATH)
    yield adapter
    
    # Teardown
    # Note: Kuzu might hold lock, so cleanup might fail in Windows, but Linux usually ok.
    # explicit close if method existed, but kuzu auto-closes on gc broadly.
    adapter.conn = None
    adapter.db = None
    # shutil.rmtree(QUERY_PATH, ignore_errors=True)

def test_initialization(adapter):
    assert adapter.db is not None
    assert adapter.conn is not None

def test_add_and_query_flow(adapter):
    # adapter.add_user_if_not_exists("user_1", "Test User") -> Removed
    adapter.conn.execute("MERGE (u:User {id: 'user_1'}) ON CREATE SET u.name = 'Test User'")
    
    # adapter.add_event(...) -> record_user_event
    adapter.record_user_event("user_1", "TEST_MSG", {"content": "Hello Graph"})
    
    results = adapter.query_recent_context("user_1")
    assert len(results) == 1
    assert "Hello Graph" in results[0]["metadata"]
    assert results[0]["type"] == "TEST_MSG"
