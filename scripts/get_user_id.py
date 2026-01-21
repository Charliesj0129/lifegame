import asyncio
import os
import sys

# Ensure app is in path
sys.path.append(os.getcwd())

from sqlalchemy import text

from app.core.database import AsyncSessionLocal


async def main():
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT id, name FROM users LIMIT 1"))
            user = result.fetchone()
            if user:
                print(f"FOUND_USER_ID: {user[0]}")
                print(f"FOUND_USER_NAME: {user[1]}")
            else:
                print("NO_USERS_FOUND")
    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
