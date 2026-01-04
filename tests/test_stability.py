import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import settings


def _run_migrations(db_url: str) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = Config(str(repo_root / "alembic.ini"))
    original_url = settings.DATABASE_URL
    settings.DATABASE_URL = db_url
    try:
        command.upgrade(config, "head")
    finally:
        settings.DATABASE_URL = original_url


def test_migration_idempotency(tmp_path):
    """
    Verifies that alembic upgrade can be run multiple times without crashing.
    """
    db_file = tmp_path / "test_stability.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    _run_migrations(db_url)

    conn = sqlite3.connect(db_file)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        row = cursor.fetchone()
        assert row and row[0] == "users"
    finally:
        conn.close()

    _run_migrations(db_url)
