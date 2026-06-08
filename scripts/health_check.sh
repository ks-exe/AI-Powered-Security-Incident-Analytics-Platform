#!/bin/bash
# Service Health Check Script
# Checks all platform services and reports their status.
# Usage: ./scripts/health_check.sh [--check-freshness]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

CHECK_FRESHNESS=false
if [ "$1" = "--check-freshness" ]; then
    CHECK_FRESHNESS=true
fi

echo "=== Security Analytics Platform — Service Health Check ==="
echo ""

SERVICES=(
    "MinIO API|http://localhost:9000/minio/health/live"
    "Nessie Catalog|http://localhost:19120/api/v2/config"
    "Apache Superset|http://localhost:8088/health"
    "Dagster Webserver|http://localhost:3000/server_info"
    "Cube.js API|http://localhost:4000/readyz"
)

HEALTHY=0
UNHEALTHY=0
TOTAL=${#SERVICES[@]}

for service_entry in "${SERVICES[@]}"; do
    IFS='|' read -r name url <<< "$service_entry"
    
    if curl -sf --connect-timeout 5 --max-time 10 "$url" > /dev/null 2>&1; then
        printf "${GREEN}✓${NC} %-20s %s\n" "$name" "healthy"
        HEALTHY=$((HEALTHY + 1))
    else
        printf "${RED}✗${NC} %-20s %s\n" "$name" "unhealthy"
        UNHEALTHY=$((UNHEALTHY + 1))
    fi
done

echo ""
echo "─────────────────────────────────────"
echo "Total: $TOTAL | Healthy: $HEALTHY | Unhealthy: $UNHEALTHY"

if [ "$CHECK_FRESHNESS" = true ]; then
    echo ""
    echo "=== Data Freshness Check ==="
    if [ -f "data/security_analytics.duckdb" ]; then
        LAST_MODIFIED=$(stat -c %Y "data/security_analytics.duckdb" 2>/dev/null || stat -f %m "data/security_analytics.duckdb" 2>/dev/null || echo "0")
        NOW=$(date +%s)
        AGE_HOURS=$(( (NOW - LAST_MODIFIED) / 3600 ))
        if [ "$AGE_HOURS" -gt 24 ]; then
            printf "${YELLOW}⚠${NC}  Database last updated %d hours ago (SLA: 24h)\n" "$AGE_HOURS"
        else
            printf "${GREEN}✓${NC}  Database last updated %d hours ago\n" "$AGE_HOURS"
        fi
    else
        printf "${RED}✗${NC}  Database file not found\n"
    fi
fi

echo ""
if [ "$UNHEALTHY" -gt 0 ]; then
    exit 1
fi
