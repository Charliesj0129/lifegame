import asyncio
import os
import sys
import random
import logging
import datetime
from typing import List
from concurrent.futures import ThreadPoolExecutor

# --- CONFIG (TEST ENV) ---
os.environ["KUZU_DATABASE_PATH"] = "/tmp/lifegame_chaos_kuzu"
os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite+aiosqlite:///:memory:"
os.environ["TESTING"] = "1"

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ChaosMonkey")

# --- MOCKS & IMPORTS ---
# We need to bootstrap the app partially
from app.main import app
from legacy.services.user_service import user_service
from legacy.services.quest_service import quest_service
from legacy.services.shop_service import shop_service
from application.services.loot_service import loot_service
from app.core.database import AsyncSessionLocal, engine
from app.models.base import Base
# from sqlalchemy.ext.asyncio import create_async_engine # Remove dup engine


async def setup_db():
    # Use the application's engine to create tables in the SAME memory space
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


async def test_addiction_eomm():
    """Test 1: Verify EOMM (Churn Risk -> High Loot)"""
    logger.info(">>> Test 1: Addiction Algorithm (EOMM/Churn) <<<")
    async with AsyncSessionLocal() as session:
        # Create User with OLD last_active
        u = await user_service.get_or_create_user(session, "user_churned")
        u.last_active_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)
        await session.commit()

        # Determine multiplier via LootService (Internal check or Quest flow)
        # We simulate the logic inside QuestService manually or call LootService with risk
        # churn_risk = "HIGH" # Derived from logic -> Unused

        # Call calculate_reward
        loot = loot_service.calculate_reward("C", "C", churn_risk="HIGH")

        if loot.xp >= 100:  # Base C=50, 2x = 100
            logger.info(f"✅ EOMM Triggered! XP: {loot.xp} (Expected ~100 with 2x)")
        else:
            logger.error(f"❌ EOMM Failed! XP: {loot.xp} (Expected ~100)")


async def test_rpe_distribution():
    """Test 2: RPE Distribution (Monte Carlo)"""
    logger.info(">>> Test 2: RPE Distribution (1000 Runs) <<<")
    jackpots = 0
    total = 1000
    for _ in range(total):
        loot = loot_service.calculate_reward("C", "C", churn_risk="LOW")
        if loot.narrative_flavor == "Jackpot":
            jackpots += 1

    rate = (jackpots / total) * 100
    logger.info(f"Jackpot Rate: {rate:.1f}% (Target ~5.0%)")
    if 3.0 <= rate <= 7.0:
        logger.info("✅ RPE Variance Normal")
    else:
        logger.warning("⚠️ RPE Variance Abnormal")


async def test_economy_race_condition():
    """Test 3: Shop Double Spend (Race Condition)"""
    logger.info(">>> Test 3: Economy Race Condition <<<")

    # Setup: User with 100 Gold. Item costs 100.
    async with AsyncSessionLocal() as session:
        u = await user_service.get_or_create_user(session, "user_greedy")
        u.gold = 100
        await session.commit()

    # We can't really test async race condition easily in single event loop provided by asyncio run
    # But we can simulate "Check then Act" gap?
    # Actually, shop_service.buy_item logic:
    # 1. Fetch User (await)
    # 2. Check Gold
    # 3. Deduct
    # 4. Commit
    # If we launch 5 async tasks simultaneously, they might all fetch user with 100 Gold before any commits?

    async def attempt_buy():
        async with AsyncSessionLocal():  # Unused session removed
            # Mock Item cost = 100
            # We need a real item in DB or mock shop service?
            # ShopService usually needs Item DB.
            # We'll mock the internal logic slightly or assume ID 1 exists and costs 100.
            # Actually, ShopService calls `item_repo`?
            # Let's Skip full mock and just check `user.gold` logic pattern
            pass

    logger.info("⚠️ Skipping rigorous Race Test in this script (Requires complex Item Setup).")
    logger.info("   Audit Finding: 'buy_item' does NOT Use Row Locking (SELECT FOR UPDATE). Risk Confirm.")


async def test_security_auth():
    """Test 4: Security (Auth Bypass)"""
    logger.info(">>> Test 4: Security (Auth Bypass) <<<")
    # Using TestClient
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # 1. Nerves NPCs (Public)
    resp = client.get("/api/nerves/npcs")
    if resp.status_code == 200:
        logger.warning(f"⚠️ /api/nerves/npcs is PUBLIC (Status 200). Info Leak: {len(resp.json().get('npcs', []))} NPCs")
    else:
        logger.info(f"✅ /api/nerves/npcs Protected? {resp.status_code}")

    # 2. Nerves Perceive (Protected)
    resp = client.post("/api/nerves/perceive", json={"trigger": "test"}, headers={"X-LifeGame-Token": "WRONG"})
    if resp.status_code == 401:
        logger.info("✅ /api/nerves/perceive Blocked Invalid Token (401)")
    else:
        logger.error(f"❌ /api/nerves/perceive ALLOWED Invalid Token ({resp.status_code})")


async def main():
    await setup_db()

    await test_addiction_eomm()
    await test_rpe_distribution()
    await test_economy_race_condition()
    await test_security_auth()


if __name__ == "__main__":
    asyncio.run(main())
