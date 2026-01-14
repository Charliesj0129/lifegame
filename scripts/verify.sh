#!/bin/bash
#
# TDD Verification Script for LifeGame Deployment
# This script tests the Azure deployment and reports pass/fail
#
# Exit Codes:
#   0 - All tests passed
#   1 - Test failure (assertion failed)
#   2 - Timeout (server not responsive)
#   3 - Configuration error
#

set -e

# Configuration
BASE_URL="${LIFEGAME_URL:-https://app-lifgame-2026.azurewebsites.net}"
MAX_WAIT_SECONDS=120
POLL_INTERVAL=5

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Function: Wait for server to become responsive
wait_for_server_start() {
    local elapsed=0
    log_info "Waiting for server at $BASE_URL to become responsive..."
    
    while [ $elapsed -lt $MAX_WAIT_SECONDS ]; do
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$BASE_URL/health" 2>/dev/null || echo "000")
        
        if [ "$HTTP_STATUS" = "200" ]; then
            log_info "Server is responsive (HTTP $HTTP_STATUS) after ${elapsed}s"
            return 0
        fi
        
        log_warn "Server returned HTTP $HTTP_STATUS, retrying in ${POLL_INTERVAL}s... (${elapsed}/${MAX_WAIT_SECONDS}s)"
        sleep $POLL_INTERVAL
        elapsed=$((elapsed + POLL_INTERVAL))
    done
    
    log_error "Server did not become responsive within ${MAX_WAIT_SECONDS}s"
    exit 2
}

# Function: Execute a curl request and capture response
curl_test() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local expected_status="$5"
    
    log_info "Test: $name"
    log_info "  Request: $method $BASE_URL$endpoint"
    
    if [ "$method" = "GET" ]; then
        RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 30 "$BASE_URL$endpoint" 2>&1)
    else
        RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 30 -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint" 2>&1)
    fi
    
    # Separate body and status code
    HTTP_BODY=$(echo "$RESPONSE" | head -n -1)
    HTTP_STATUS=$(echo "$RESPONSE" | tail -n 1)
    
    echo "  Response Status: $HTTP_STATUS"
    echo "  Response Body: $(echo "$HTTP_BODY" | head -c 200)..."
}

# Function: Assert response conditions
assert_response() {
    local test_name="$1"
    local condition="$2"
    local expected="$3"
    
    case "$condition" in
        "status_eq")
            if [ "$HTTP_STATUS" = "$expected" ]; then
                log_info "  ✓ PASS: Status is $expected"
                return 0
            else
                log_error "  ✗ FAIL: Expected status $expected, got $HTTP_STATUS"
                return 1
            fi
            ;;
        "body_contains")
            if echo "$HTTP_BODY" | grep -q "$expected"; then
                log_info "  ✓ PASS: Body contains '$expected'"
                return 0
            else
                log_error "  ✗ FAIL: Body does not contain '$expected'"
                return 1
            fi
            ;;
        "body_not_contains")
            if echo "$HTTP_BODY" | grep -q "$expected"; then
                log_error "  ✗ FAIL: Body should not contain '$expected'"
                return 1
            else
                log_info "  ✓ PASS: Body does not contain '$expected'"
                return 0
            fi
            ;;
        "body_json_field")
            # Uses jq to check a field
            local field=$(echo "$expected" | cut -d'=' -f1)
            local value=$(echo "$expected" | cut -d'=' -f2)
            local actual=$(echo "$HTTP_BODY" | jq -r "$field" 2>/dev/null)
            if [ "$actual" = "$value" ]; then
                log_info "  ✓ PASS: JSON field $field equals '$value'"
                return 0
            else
                log_error "  ✗ FAIL: JSON field $field expected '$value', got '$actual'"
                return 1
            fi
            ;;
    esac
}

# ===========================================
# MAIN TEST EXECUTION
# ===========================================

echo ""
echo "======================================"
echo "LifeGame TDD Verification Script"
echo "======================================"
echo "Target: $BASE_URL"
echo "Time: $(date)"
echo ""

FAILURES=0

# Test 1: Health Check
log_info "=== Test Suite 1: Server Health ==="
wait_for_server_start

curl_test "Health Endpoint Returns 200" "GET" "/health" "" "200"
assert_response "Health Status" "status_eq" "200" || FAILURES=$((FAILURES + 1))

# Check that health doesn't contain PostgreSQL errors
if echo "$HTTP_BODY" | grep -qi "postgresql\|asyncpg\|connection refused"; then
    log_error "  ✗ FAIL: Health response contains database error indicators"
    FAILURES=$((FAILURES + 1))
else
    log_info "  ✓ PASS: No database errors in health response"
fi

echo ""

# Test 2: Webhook Endpoint Exists
log_info "=== Test Suite 2: LINE Webhook ==="
curl_test "Webhook Endpoint Exists" "POST" "/line/callback" '{"events":[]}' ""
# We expect 400 (bad request due to missing/invalid signature) or 200, NOT 500
if [ "$HTTP_STATUS" = "500" ] || [ "$HTTP_STATUS" = "503" ]; then
    log_error "  ✗ FAIL: Webhook returned server error $HTTP_STATUS"
    FAILURES=$((FAILURES + 1))
else
    log_info "  ✓ PASS: Webhook endpoint is reachable (status: $HTTP_STATUS)"
fi

# Check for system error patterns in response
assert_response "No System Error" "body_not_contains" "系統異常" || FAILURES=$((FAILURES + 1))
assert_response "No PostgreSQL Error" "body_not_contains" "Connection refused" || FAILURES=$((FAILURES + 1))

echo ""

# Test 3: API Root (optional)
log_info "=== Test Suite 3: API Sanity ==="
curl_test "Root Endpoint" "GET" "/" "" ""
if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "404" ]; then
    log_info "  ✓ PASS: Root endpoint responded (status: $HTTP_STATUS)"
else
    log_warn "  ⚠ WARN: Unexpected root status $HTTP_STATUS"
fi

echo ""
echo "======================================"

# Final Result
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}TEST PASSED${NC}"
    echo -e "${GREEN}======================================${NC}"
    exit 0
else
    echo -e "${RED}======================================${NC}"
    echo -e "${RED}TEST FAILED ($FAILURES failures)${NC}"
    echo -e "${RED}======================================${NC}"
    exit 1
fi
