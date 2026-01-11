import pytest
import os
from unittest.mock import MagicMock


# Use a separate test db for graph tests
TEST_DB_PATH = "./test_kuzu_graph_chain_db"


@pytest.fixture
def graph_adapter():
    # Nuclear Isolation: Load Class from Source directly
    import importlib.util

    adapter_path = os.path.join(os.getcwd(), "adapters/persistence/kuzu/adapter.py")
    spec = importlib.util.spec_from_file_location("adapters.persistence.kuzu.adapter", adapter_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    KuzuAdapter = module.KuzuAdapter

    def cleanup():
        if os.path.exists(TEST_DB_PATH):
            import shutil

            if os.path.isdir(TEST_DB_PATH):
                shutil.rmtree(TEST_DB_PATH)
            else:
                os.remove(TEST_DB_PATH)

    cleanup()  # Pre-cleanup

    adapter = KuzuAdapter(db_path=TEST_DB_PATH)
    yield adapter

    # Post-cleanup
    cleanup()


def test_add_quest_dependency(graph_adapter):
    """Test creating REQUIRES relationship"""
    # Create seeds
    graph_adapter.add_node("Quest", {"id": "Q_A", "title": "Quest A", "status": "ACTIVE"})
    graph_adapter.add_node("Quest", {"id": "Q_B", "title": "Quest B", "status": "LOCKED"})

    # Add dependency: B requires A
    success = graph_adapter.add_quest_dependency("Q_B", "Q_A")
    assert success is True

    # Verify relationship exists
    result = graph_adapter.query("MATCH (b:Quest {id: 'Q_B'})-[:REQUIRES]->(a:Quest {id: 'Q_A'}) RETURN a.id")
    assert len(result) == 1
    assert result[0][0] == "Q_A"


def test_get_unlockable_templates(graph_adapter):
    """Test unlocking logic"""
    user_id = "test_user"

    # Setup Protocol:
    # Q1 (Base) -> Q2 -> Q3
    # Q4 (Base)

    # 1. Seed Quests
    graph_adapter.add_node("Quest", {"id": "Q1", "title": "Base Q1"})
    graph_adapter.add_node("Quest", {"id": "Q2", "title": "Chain Q2"})
    graph_adapter.add_node("Quest", {"id": "Q3", "title": "Chain Q3"})
    graph_adapter.add_node("Quest", {"id": "Q4", "title": "Base Q4"})

    # 2. Add Dependencies
    graph_adapter.add_quest_dependency("Q2", "Q1")  # Q2 requires Q1
    graph_adapter.add_quest_dependency("Q3", "Q2")  # Q3 requires Q2

    # 3. Initial State: User has done nothing
    # Q1 and Q4 should be unlockable (Base)
    # Q2, Q3 locked
    unlockables = graph_adapter.get_unlockable_templates(user_id)
    ids = sorted([u["id"] for u in unlockables])
    assert "Q1" in ids
    assert "Q4" in ids
    assert "Q2" not in ids
    assert "Q3" not in ids

    # 4. User Complete Q1
    # Mock completion relationship
    graph_adapter.conn.execute(f"CREATE (u:User {{id: '{user_id}', name: '{user_id}'}})")
    graph_adapter.conn.execute(
        f"MATCH (u:User {{name: '{user_id}'}}), (q:Quest {{id: 'Q1'}}) CREATE (u)-[:COMPLETED]->(q)"
    )

    # Q1 now completed, should NOT be in unlockables
    # Q2 should now be unlocked
    unlockables = graph_adapter.get_unlockable_templates(user_id)
    ids = sorted([u["id"] for u in unlockables])

    assert "Q1" not in ids  # Already done
    assert "Q4" in ids  # Still unlockable base
    assert "Q2" in ids  # UNLOCKED!
    assert "Q3" not in ids  # Still locked (needs Q2)

    # 5. User Complete Q2
    graph_adapter.conn.execute(
        f"MATCH (u:User {{name: '{user_id}'}}), (q:Quest {{id: 'Q2'}}) CREATE (u)-[:COMPLETED]->(q)"
    )

    unlockables = graph_adapter.get_unlockable_templates(user_id)
    ids = [u["id"] for u in unlockables]

    assert "Q2" not in ids
    assert "Q3" in ids  # UNLOCKED!
