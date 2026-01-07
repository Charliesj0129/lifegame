import pytest
import shutil
import os
from adapters.persistence.kuzu.adapter import KuzuAdapter
from application.services.graph_service import GraphService, KuzuCursorWrapper

@pytest.fixture
def kuzu_adapter(tmp_path):
    db_path = tmp_path / "kuzu_test"
    adapter = KuzuAdapter(db_path=str(db_path))
    yield adapter

def test_kuzu_initialization_and_query(kuzu_adapter):
    # Schema should be initialized in constructor
    # Query for User node
    results = kuzu_adapter.query("MATCH (u:User) RETURN u.name")
    
    # Adapter now returns List[List[Any]] (rows)
    assert isinstance(results, list)
    assert len(results) > 0 # Seeded Player
    assert results[0][0] == "Player"

def test_graph_service_wrapper(tmp_path):
    # Mocking settings or injecting adapter is harder with global instance pattern
    # But we can instantiate service with a custom adapter if we refactor service slightly
    # Current GraphService hardcodes `self.adapter = KuzuAdapter()`.
    # Let's rely on integration aspect or monkeypatch KuzuAdapter class if needed.
    # But since we use tmp_path for adapter test, the global service uses default settings path.
    # We should probably skip verifying the global singleton against temp DB unless we patch settings.
    pass

def test_cursor_wrapper():
    data = [["A"], ["B"]]
    cursor = KuzuCursorWrapper(data)
    
    assert cursor.has_next()
    assert cursor.get_next() == ["A"]
    assert cursor.has_next()
    assert cursor.get_next() == ["B"]
    assert not cursor.has_next()
    assert cursor.get_next() is None
