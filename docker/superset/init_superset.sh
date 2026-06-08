#!/bin/bash
set -e

echo "Initializing Apache Superset..."

# Wait for Superset metadata database to be ready
sleep 10

# Initialize the database (run migrations)
superset db upgrade

# Create admin user with RBAC admin role
superset fab create-admin \
    --username "${SUPERSET_ADMIN_USER:-admin}" \
    --firstname Admin \
    --lastname User \
    --email admin@security-analytics.local \
    --password "${SUPERSET_ADMIN_PASSWORD:-admin123}" || true

# Initialize default roles and permissions (sets up RBAC)
superset init

# Add DuckDB database connection (MVP - direct connection to Gold layer)
superset set-database-uri \
    --database-name "Security Analytics DuckDB" \
    --uri "duckdb:////app/data/security_analytics.duckdb" || true

echo "Superset initialization complete!"
echo "Access the dashboard at http://localhost:8088"
echo "Login with: ${SUPERSET_ADMIN_USER:-admin} / ${SUPERSET_ADMIN_PASSWORD:-admin123}"
