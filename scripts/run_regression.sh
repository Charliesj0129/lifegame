#!/bin/bash
set -e

echo "============================================"
echo "    LIFEOS REGRESSION SUITE"
echo "============================================"
echo "Testing Environment: $TESTING_ENV"

# 1. Unit Tests
echo ""
echo ">>> [1/4] Running UNIT Tests..."
uv run pytest tests/unit -v
echo ">>> Unit Tests PASSED."

# 2. Integration Tests
echo ""
echo ">>> [2/4] Running INTEGRATION Tests..."
# Requires Mock DB or Testconatiners. Handled by fixtures.
uv run pytest tests/integration -v
echo ">>> Integration Tests PASSED."

# 3. System Tests
echo ""
echo ">>> [3/4] Running SYSTEM Tests (E2E)..."
uv run pytest tests/system -v
echo ">>> System Tests PASSED."

# 4. Blackbox Tests
echo ""
echo ">>> [4/4] Running BLACKBOX Tests (Contract based)..."
uv run pytest tests/blackbox -v
echo ">>> Blackbox Tests PASSED."

echo ""
echo "============================================"
echo "    ALL REGRESSION CHECKS PASSED ✅"
echo "============================================"
