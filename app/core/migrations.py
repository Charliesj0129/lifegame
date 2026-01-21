import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    config_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    cfg = Config(str(config_path))
    command.upgrade(cfg, "head")
