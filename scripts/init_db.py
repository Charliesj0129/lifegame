import logging
import subprocess
import sys
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db():
    try:
        logger.info("Initializing database...")
        # Run alembic upgrade head
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        logger.info("Database initialized successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    init_db()
