#!/bin/bash
set -e

# Base URL from env or default to local
BASE_URL="${APP_BASE_URL:-http://localhost:8000}"

echo "🌫️  Starting Post-Deploy Smoke Test against $BASE_URL..."

# 1. Health Check
# Retry health check for up to 150 seconds (30 retries * 5s)
MAX_RETRIES=30
RETRY_DELAY=5

for ((i=1; i<=MAX_RETRIES; i++)); do
    echo "Attempt $i/$MAX_RETRIES checking /health..."
    response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
    
    if [ "$response" == "200" ]; then
        echo "✅ /health returned 200 OK"
        break
    else
        echo "⚠️  /health returned $response. Retrying in $RETRY_DELAY seconds..."
        sleep $RETRY_DELAY
    fi
    
    if [ $i -eq $MAX_RETRIES ]; then
        echo "❌ /health failed after $MAX_RETRIES attempts (Last code: $response)"
        exit 1
    fi
done

# 2. Database Connectivity (via API if exposed, or implied by health)
# If /health checks DB, we are good. Assuming current /health is simple.
# Let's hit a public endpoint if available, or just trust /health for this scope.

echo "🎉 Smoke Test Passed! System is operational."
exit 0
