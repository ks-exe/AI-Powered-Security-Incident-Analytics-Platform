#!/bin/bash
set -e

echo "=== Security Analytics Platform Setup ==="
echo ""

# ─── Check Docker ─────────────────────────────────────────────────────────────
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not in PATH."
    echo "Please install Docker Engine 24+ from https://docs.docker.com/get-docker/"
    exit 1
fi

DOCKER_VERSION=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0")
DOCKER_MAJOR=$(echo "$DOCKER_VERSION" | cut -d. -f1)
if [ "$DOCKER_MAJOR" -lt 24 ] 2>/dev/null; then
    echo "WARNING: Docker version $DOCKER_VERSION detected. Recommended: 24+"
fi
echo "  ✓ Docker installed (version: $DOCKER_VERSION)"

# ─── Check Docker Compose ─────────────────────────────────────────────────────
if ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose v2 is not available."
    echo "Please install Docker Compose v2+ from https://docs.docker.com/compose/install/"
    exit 1
fi

COMPOSE_VERSION=$(docker compose version --short 2>/dev/null || echo "unknown")
echo "  ✓ Docker Compose installed (version: $COMPOSE_VERSION)"

# ─── Check RAM ────────────────────────────────────────────────────────────────
REQUIRED_RAM_GB=16

if [ "$(uname)" = "Darwin" ]; then
    TOTAL_RAM_KB=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
    TOTAL_RAM_GB=$((TOTAL_RAM_KB / 1073741824))
elif [ "$(uname)" = "Linux" ]; then
    TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}')
    TOTAL_RAM_GB=$((TOTAL_RAM_KB / 1048576))
else
    # Windows / other - attempt wmic
    TOTAL_RAM_BYTES=$(wmic computersystem get TotalPhysicalMemory 2>/dev/null | grep -o '[0-9]*' | head -1)
    if [ -n "$TOTAL_RAM_BYTES" ]; then
        TOTAL_RAM_GB=$((TOTAL_RAM_BYTES / 1073741824))
    else
        echo "WARNING: Could not determine system RAM. Minimum requirement: ${REQUIRED_RAM_GB}GB"
        TOTAL_RAM_GB=$REQUIRED_RAM_GB
    fi
fi

if [ "$TOTAL_RAM_GB" -lt "$REQUIRED_RAM_GB" ]; then
    echo "ERROR: Insufficient RAM. Found: ${TOTAL_RAM_GB}GB, Required: ${REQUIRED_RAM_GB}GB"
    echo "The platform requires at least 16GB RAM to run all services."
    exit 1
fi
echo "  ✓ RAM: ${TOTAL_RAM_GB}GB available (minimum: ${REQUIRED_RAM_GB}GB)"

# ─── Check Disk Space ─────────────────────────────────────────────────────────
REQUIRED_DISK_GB=20

if [ "$(uname)" = "Darwin" ] || [ "$(uname)" = "Linux" ]; then
    AVAILABLE_DISK_KB=$(df -k . 2>/dev/null | tail -1 | awk '{print $4}')
    AVAILABLE_DISK_GB=$((AVAILABLE_DISK_KB / 1048576))
else
    # Windows fallback
    AVAILABLE_DISK_GB=$REQUIRED_DISK_GB
    echo "WARNING: Could not determine available disk space. Minimum requirement: ${REQUIRED_DISK_GB}GB"
fi

if [ "$AVAILABLE_DISK_GB" -lt "$REQUIRED_DISK_GB" ]; then
    echo "ERROR: Insufficient disk space. Found: ${AVAILABLE_DISK_GB}GB, Required: ${REQUIRED_DISK_GB}GB"
    echo "The platform requires at least 20GB free disk space."
    exit 1
fi
echo "  ✓ Disk space: ${AVAILABLE_DISK_GB}GB available (minimum: ${REQUIRED_DISK_GB}GB)"

# ─── Check Docker Daemon ──────────────────────────────────────────────────────
if ! docker info &> /dev/null; then
    echo "ERROR: Docker daemon is not running."
    echo "Please start Docker Desktop or the Docker service."
    exit 1
fi
echo "  ✓ Docker daemon is running"

# ─── Setup Complete ───────────────────────────────────────────────────────────
echo ""
echo "=== All prerequisites met ==="
echo ""
echo "System Requirements:"
echo "  - Docker Engine: 24+ (found: $DOCKER_VERSION)"
echo "  - Docker Compose: v2+ (found: $COMPOSE_VERSION)"
echo "  - RAM: 16GB minimum (found: ${TOTAL_RAM_GB}GB)"
echo "  - Disk: 20GB minimum (found: ${AVAILABLE_DISK_GB}GB)"
echo ""
echo "To start the full platform:"
echo "  docker compose up -d"
echo ""
echo "To start the lite profile (MinIO + Nessie only):"
echo "  docker compose -f docker-compose.lite.yml up -d"
echo ""
echo "=== Setup validation complete ==="
