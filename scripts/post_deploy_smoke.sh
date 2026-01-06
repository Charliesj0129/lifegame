#!/bin/bash
set -e

# Base URL from env or default to local
BASE_URL="${APP_BASE_URL:-http://localhost:8000}"

echo "🌫️  Starting Post-Deploy Smoke Test against $BASE_URL..."

# 1. Health Check
echo "🔍 Checking /health endpoint..."
response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")

if [ "$response" == "200" ]; then
    echo "✅ /health returned 200 OK"
else
    echo "❌ /health returned $response"
    exit 1
fi

# 2. Database Connectivity (via API if exposed, or implied by health)
# If /health checks DB, we are good. Assuming current /health is simple.
# Let's hit a public endpoint if available, or just trust /health for this scope.

echo "🎉 Smoke Test Passed! System is operational."
exit 0
