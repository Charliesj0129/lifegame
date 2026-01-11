import asyncio
import logging
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

# Configure Source (Postgres) and Target (SQLite)
# In run-time, these would be loaded from distinct env vars or arguments.
# For template purposes, we assume settings.DATABASE_URL or similar.

SOURCE_DB_URI = os.getenv("SOURCE_DB_URI", "postgresql+asyncpg://user:pass@host:5432/db")
TARGET_DB_URI = "sqlite+aiosqlite:///./data/game.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_data():
    source_engine = create_async_engine(SOURCE_DB_URI, echo=False)
    target_engine = create_async_engine(TARGET_DB_URI, echo=False)

    tables_to_migrate = [
        "users", "quests", "items", "logs_user"
        # Add all tables in dependency order
    ]

    async with source_engine.connect() as src_conn, target_engine.connect() as tgt_conn:
        for table in tables_to_migrate:
            logger.info(f"Migrating table: {table}")
            try:
                # 1. Fetch from Source
                result = await src_conn.execute(text(f"SELECT * FROM {table}"))
                rows = result.fetchall()
                keys = result.keys()
                
                if not rows:
                    logger.info(f"No rows in {table}")
                    continue

                # 2. Transform Data (UUID -> str, JSON -> str/dict handled by driver?)
                # SQLite+aiosqlite usually handles str for UUID if column is VARCHAR/CHAR.
                # If column is BLOB, we might need bytes.
                # Assuming SQLAlchemy Standard Types will be created in Target.
                
                data_to_insert = []
                for row in rows:
                    row_dict = dict(zip(keys, row))
                    # Basic transformations if needed
                    for k, v in row_dict.items():
                        if hasattr(v, "hex"): # UUID
                             row_dict[k] = str(v)
                        # JSON fields often come as dict/list from asyncpg, 
                        # but sqlite might need JSON dump if using legacy drivers, 
                        # but aiosqlite+JSON type usually works.
                    data_to_insert.append(row_dict)

                # 3. Insert into Target
                # Use Table reflection to get table object for proper insert
                # But here we use raw text insert for universality OR metadata reflection.
                # Let's use metadata reflection for safety if possible, OR generic insert.
                # Generic insert:
                from sqlalchemy import table as sql_table, column
                t_obj = sql_table(table, *[column(k) for k in keys])
                
                # Batch insert
                BATCH_SIZE = 1000
                for i in range(0, len(data_to_insert), BATCH_SIZE):
                    batch = data_to_insert[i:i+BATCH_SIZE]
                    # We utilize the target table structure.
                    # Actually, raw SQL is risky if schemas differ.
                    # Best: Use proper Insert statement.
                    
                    # We construct specific insert statement
                    # Insert(t_obj).values(batch)
                    
                    from sqlalchemy import insert
                    stmt = insert(t_obj).values(batch)
                    await tgt_conn.execute(stmt)
                    await tgt_conn.commit()
                
                logger.info(f"Migrated {len(data_to_insert)} rows for {table}.")
                
            except Exception as e:
                logger.error(f"Failed to migrate {table}: {e}")
                
    await source_engine.dispose()
    await target_engine.dispose()

if __name__ == "__main__":
    import os
    if "SOURCE_DB_URI" not in os.environ:
        logger.warning("SOURCE_DB_URI not set. Running in Template Mode.")
    else:
        asyncio.run(migrate_data())
