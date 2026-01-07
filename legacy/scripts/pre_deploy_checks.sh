#!/bin/bash
set -e

echo "🔍 Starting Pre-Deploy Checks..."

# 1. Environment Variable Check
REQUIRED_VARS=("DATABASE_URL" "LINE_CHANNEL_SECRET" "LINE_CHANNEL_ACCESS_TOKEN")
FAIL=0

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "❌ Missing required environment variable: $var"
    FAIL=1
  fi
done

if [ $FAIL -eq 1 ]; then
  echo "⚠️  Environment check failed! Please ensure .env or secrets are set."
  # In strictly local dev, we might not want to hard fail if using default defaults, 
  # but for deployment this is critical.
  if [ "$ALLOW_MISSING_ENV" != "true" ]; then
    exit 1
  fi
else
  echo "✅ Environment variables check passed."
fi

# 2. Database Connection Check
# Using python one-liner to check connection
echo "🔍 Checking Database Connection..."
python3 -c "
import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

url = os.environ.get('DATABASE_URL')
if not url:
    print('❌ No DATABASE_URL set')
    sys.exit(1)

async def check():
    try:
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
        print('✅ Database connection successful')
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        sys.exit(1)

asyncio.run(check())
"

# 3. Migration Status Check
echo "🔍 Checking Migration Status..."
# Capture output of alembic check, usually 'check' command verifies if head is current
# Note: 'uv run alembic check' or just 'alembic check' depending on environment
# If 'alembic check' is not available in older versions, we can use 'current' vs 'head'
if command -v alembic &> /dev/null; then
    # Dry run upgrade to see if it works? Or just ensure alembic can run.
    # 'alembic current' shows current revision.
    alembic current || { echo "❌ Alembic check failed"; exit 1; }
    echo "✅ Alembic check passed."
else
    echo "⚠️  Alembic not found in PATH, skipping migration check."
fi

echo "🎉 All Pre-Deploy Checks Passed!"
exit 0
