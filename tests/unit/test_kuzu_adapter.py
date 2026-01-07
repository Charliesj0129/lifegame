import pytest
import shutil
import time
from adapters.persistence.kuzu_adapter import KuzuAdapter

QUERY_PATH = "./test_kuzu_db"

@pytest.fixture
def adapter():
    # Setup
    import os
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
    adapter.add_user_if_not_exists("user_1", "Test User")
    
    ts = int(time.time())
    adapter.add_event("user_1", "evt_1", "TEST_MSG", "Hello Graph", ts)
    
    results = adapter.query_recent_context("user_1")
    assert len(results) == 1
    assert results[0]["content"] == "Hello Graph"
    assert results[0]["type"] == "TEST_MSG"
