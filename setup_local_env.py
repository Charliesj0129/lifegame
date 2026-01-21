import asyncio
import logging
import os
import subprocess
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def check_port(port: int = 8000):
    """Check if port is occupied."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("localhost", port)) == 0:
            logger.warning(f"⚠️  Port {port} is currently in use. You may need to restart the server after setup.")
            return True
        else:
            logger.info(f"✅ Port {port} is free.")
            return False


async def clean_and_seed_db():
    """Clean database and seed initial test data."""
    logger.info("🧹 Cleaning and Resetting Database...")

    # Use config URI (likely SQLite in local, or Postgres if configured)
    db_url = settings.SQLALCHEMY_DATABASE_URI
    if not db_url:
        logger.error("❌ SQLALCHEMY_DATABASE_URI not checked in settings.")
        sys.exit(1)

    engine = create_async_engine(db_url)

    async with engine.begin() as conn:
        # 1. Truncate/Delete Tables (Order matters for Foreign Keys)
        # We delete all rows to keep schema intact (faster than drop_all/create_all)
        # Note: Order dependent on foreign keys (UserItem -> Item, UserItem -> User, Quest -> User)
        tables = [
            "user_items",
            "quests",
            "habit_states",  # Verify this one
            "items",
            "users",
        ]

        for table in tables:
            try:
                # SQLite doesn't support TRUNCATE, using DELETE
                await conn.execute(text(f"DELETE FROM {table}"))
                # Reset sequence if Postgres? SQLite auto-resets usually on vacuum or handled manually.
                # For SQLite autoincrement:
                if "sqlite" in str(db_url):
                    await conn.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
            except Exception as e:
                # Table might not exist yet if migration hasn't run or verify table name
                logger.debug(f"Info clearing table {table}: {e}")

        # 2. Seed Initial Items (for Shop Simulation)
        logger.info("🌱 Seeding Test Data (Items)...")
        # Ensure Item table exists (migrations should have run)
        items = [
            {
                "id": "POTION",
                "name": "Health Potion",
                "price": 50,
                "description": "Restores HP",
                "is_purchasable": True,
                "rarity": "COMMON",
                "type": "CONSUMABLE",
            },
            {
                "id": "SWORD",
                "name": "Wooden Sword",
                "price": 100,
                "description": "Basic weapon",
                "is_purchasable": True,
                "rarity": "COMMON",
                "type": "WEAPON",
            },
        ]

        for item in items:
            # Check if columns exist (rarity/type might be newer?)
            # Assuming standard schema
            await conn.execute(
                text(
                    "INSERT INTO items (id, name, price, description, is_purchasable, rarity, type) VALUES (:id, :name, :price, :description, :is_purchasable, :rarity, :type)"
                ),
                item,
            )

    await engine.dispose()
    logger.info("✅ Database cleaned and seeded.")


def check_env():
    """Check .env file for required keys."""
    if not os.path.exists(".env"):
        logger.warning("⚠️  .env file not found!")
    else:
        logger.info("✅ .env file found.")

    # Check keys
    # required = ["LINE_CHANNEL_SECRET", "SQLALCHEMY_DATABASE_URI"]
    # missing = [k for k in required if not getattr(settings, k, None) and k not in os.environ] (Unused)

    if settings.LINE_CHANNEL_SECRET is None:
        logger.warning("⚠️  LINE_CHANNEL_SECRET is missing. Webhook signature verification will fail.")


# Ensure models are loaded for create_all
from app.models.base import Base
from app.models.dda import HabitState
from app.models.gamification import Boss, Item, Recipe, UserItem
from app.models.quest import Quest

# Import all models to ensure they are registered with Base
from app.models.user import User

# Add other model imports as needed if they are in different modules not imported by above


async def bootstrap_schema(engine):
    """Create all tables using SQLAlchemy metadata."""
    logger.info("🏗️  Creating Schema (Base.metadata.create_all)...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Schema created.")


def run_migrations():
    """Skipping Alembic Upgrade in favor of create_all for this run."""
    # We could stamp head here if we wanted to sync alembic, but for validtion create_all is enough.
    pass


async def main():
    logger.info("🔧 Starting Local Environment Bootstrap...")

    check_env()

    # 0. Force Fresh Start (SQLite only)
    db_url = settings.SQLALCHEMY_DATABASE_URI or ""
    if "sqlite" in db_url and "game.db" in db_url:
        db_path = "data/game.db"
        if os.path.exists(db_path):
            logger.warning(f"🗑️  Deleting existing SQLite DB: {db_path}")
            os.remove(db_path)

    # 1. Create Schema
    engine = create_async_engine(db_url)
    await bootstrap_schema(engine)
    await engine.dispose()

    # 2. Seed Data
    await clean_and_seed_db()  # This will assert tables exist

    await check_port(8000)

    logger.info("🎉 Environment Setup Complete. You can now start the server: 'uv run python -m app.main'")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
