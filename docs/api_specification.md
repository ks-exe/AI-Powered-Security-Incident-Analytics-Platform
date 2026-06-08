# API Specification — Cube.js Semantic Layer

This document specifies the Cube.js REST and GraphQL API endpoints exposed by the Security Incident Analytics Platform's semantic layer.

## Base URL

```
http://localhost:4000
```

## Authentication

All API requests require a bearer token derived from the `CUBEJS_API_SECRET` environment variable.

```bash
# Generate a JWT token (in production, use proper JWT signing)
# For development mode, pass the secret directly as the token:
Authorization: Bearer your-cubejs-api-secret
```

The token is configured in `cube/.env`:

```env
CUBEJS_API_SECRET=your-cubejs-api-secret
```

In production, generate a signed JWT with the secret:

```python
import jwt

token = jwt.encode({"iat": 1700000000, "exp": 1700086400}, "your-cubejs-api-secret", algorithm="HS256")
```

---

## REST API Endpoints

### POST /cubejs-api/v1/load

Execute a query against the semantic layer. This is the primary endpoint for fetching data.

**Request:**

```bash
curl -X POST http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-cubejs-api-secret" \
  -d '{
    "query": {
      "measures": ["KpiSummary.totalAttacks"],
      "dimensions": [],
      "timeDimensions": []
    }
  }'
```

**Response:**

```json
{
  "query": {
    "measures": ["KpiSummary.totalAttacks"],
    "dimensions": [],
    "timeDimensions": []
  },
  "data": [
    { "KpiSummary.totalAttacks": 1523 }
  ],
  "annotation": {
    "measures": {
      "KpiSummary.totalAttacks": { "title": "Kpi Summary Total Attacks", "type": "number" }
    }
  }
}
```

### GET /cubejs-api/v1/meta

Retrieve metadata about all available cubes, measures, and dimensions.

**Request:**

```bash
curl http://localhost:4000/cubejs-api/v1/meta \
  -H "Authorization: Bearer your-cubejs-api-secret"
```

**Response (abbreviated):**

```json
{
  "cubes": [
    {
      "name": "KpiSummary",
      "measures": [
        { "name": "KpiSummary.totalAttacks", "type": "number" },
        { "name": "KpiSummary.failedLoginRate", "type": "number" },
        { "name": "KpiSummary.avgMttdMinutes", "type": "number" },
        { "name": "KpiSummary.avgMttrMinutes", "type": "number" },
        { "name": "KpiSummary.slaCompliance", "type": "number" }
      ],
      "dimensions": [
        { "name": "KpiSummary.computedAt", "type": "time" }
      ]
    },
    {
      "name": "AttackVolumeByDay",
      "measures": [
        { "name": "AttackVolumeByDay.attackCount", "type": "sum" },
        { "name": "AttackVolumeByDay.cumulativeAttackCount", "type": "max" }
      ],
      "dimensions": [
        { "name": "AttackVolumeByDay.eventDate", "type": "time" }
      ]
    },
    {
      "name": "AttackVolumeByCountry",
      "measures": [
        { "name": "AttackVolumeByCountry.attackCount", "type": "sum" },
        { "name": "AttackVolumeByCountry.percentageOfTotal", "type": "number" }
      ],
      "dimensions": [
        { "name": "AttackVolumeByCountry.country", "type": "string" }
      ]
    },
    {
      "name": "HourlyEventSummary",
      "measures": [
        { "name": "HourlyEventSummary.eventCount", "type": "sum" },
        { "name": "HourlyEventSummary.uniqueIps", "type": "sum" },
        { "name": "HourlyEventSummary.uniqueUsers", "type": "sum" }
      ],
      "dimensions": [
        { "name": "HourlyEventSummary.eventHour", "type": "time" },
        { "name": "HourlyEventSummary.eventType", "type": "string" }
      ]
    },
    {
      "name": "SecurityEvents",
      "measures": [
        { "name": "SecurityEvents.count", "type": "count" },
        { "name": "SecurityEvents.attackCount", "type": "count" },
        { "name": "SecurityEvents.failedLoginCount", "type": "count" },
        { "name": "SecurityEvents.uniqueIps", "type": "countDistinct" },
        { "name": "SecurityEvents.uniqueUsers", "type": "countDistinct" }
      ],
      "dimensions": [
        { "name": "SecurityEvents.eventTime", "type": "time" },
        { "name": "SecurityEvents.eventType", "type": "string" },
        { "name": "SecurityEvents.severity", "type": "string" },
        { "name": "SecurityEvents.country", "type": "string" },
        { "name": "SecurityEvents.department", "type": "string" },
        { "name": "SecurityEvents.isAttackEvent", "type": "boolean" }
      ]
    },
    {
      "name": "AnomalyResults",
      "measures": [
        { "name": "AnomalyResults.count", "type": "count" },
        { "name": "AnomalyResults.anomalyScore", "type": "avg" },
        { "name": "AnomalyResults.anomalyCount", "type": "count" },
        { "name": "AnomalyResults.totalEventCount", "type": "sum" }
      ],
      "dimensions": [
        { "name": "AnomalyResults.windowStart", "type": "time" },
        { "name": "AnomalyResults.windowEnd", "type": "time" },
        { "name": "AnomalyResults.isAnomaly", "type": "boolean" },
        { "name": "AnomalyResults.topContributingFeature", "type": "string" },
        { "name": "AnomalyResults.modelVersion", "type": "string" }
      ]
    }
  ]
}
```

### POST /cubejs-api/graphql

Execute GraphQL queries against the semantic layer.

**Endpoint:** `http://localhost:4000/cubejs-api/graphql`

---

## Example Queries

### KPI Summary — All Security KPIs

```bash
curl -X POST http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-cubejs-api-secret" \
  -d '{
    "query": {
      "measures": [
        "KpiSummary.totalAttacks",
        "KpiSummary.failedLoginRate",
        "KpiSummary.avgMttdMinutes",
        "KpiSummary.avgMttrMinutes",
        "KpiSummary.slaCompliance"
      ]
    }
  }'
```

### Attack Volume by Day — Time Series

```bash
curl -X POST http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-cubejs-api-secret" \
  -d '{
    "query": {
      "measures": ["AttackVolumeByDay.attackCount"],
      "timeDimensions": [
        {
          "dimension": "AttackVolumeByDay.eventDate",
          "granularity": "day",
          "dateRange": ["2024-01-01", "2024-01-31"]
        }
      ],
      "order": { "AttackVolumeByDay.eventDate": "asc" }
    }
  }'
```

### Attack Volume by Country — Top 10

```bash
curl -X POST http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-cubejs-api-secret" \
  -d '{
    "query": {
      "measures": ["AttackVolumeByCountry.attackCount"],
      "dimensions": ["AttackVolumeByCountry.country"],
      "order": { "AttackVolumeByCountry.attackCount": "desc" },
      "limit": 10
    }
  }'
```

### Hourly Event Summary — With Event Type Breakdown

```bash
curl -X POST http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-cubejs-api-secret" \
  -d '{
    "query": {
      "measures": [
        "HourlyEventSummary.eventCount",
        "HourlyEventSummary.uniqueIps",
        "HourlyEventSummary.uniqueUsers"
      ],
      "timeDimensions": [
        {
          "dimension": "HourlyEventSummary.eventHour",
          "granularity": "hour",
          "dateRange": "Last 7 days"
        }
      ],
      "dimensions": ["HourlyEventSummary.eventType"]
    }
  }'
```

### Security Events — Filtered by Severity and Country

```bash
curl -X POST http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-cubejs-api-secret" \
  -d '{
    "query": {
      "measures": ["SecurityEvents.count", "SecurityEvents.attackCount"],
      "dimensions": ["SecurityEvents.eventType"],
      "filters": [
        {
          "member": "SecurityEvents.severity",
          "operator": "equals",
          "values": ["critical", "high"]
        },
        {
          "member": "SecurityEvents.country",
          "operator": "equals",
          "values": ["KP", "IR", "SY"]
        }
      ],
      "timeDimensions": [
        {
          "dimension": "SecurityEvents.eventTime",
          "dateRange": "Last 30 days"
        }
      ]
    }
  }'
```

### Anomaly Results — Detected Anomalies Only

```bash
curl -X POST http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-cubejs-api-secret" \
  -d '{
    "query": {
      "measures": ["AnomalyResults.anomalyScore", "AnomalyResults.totalEventCount"],
      "dimensions": [
        "AnomalyResults.topContributingFeature",
        "AnomalyResults.modelVersion"
      ],
      "timeDimensions": [
        {
          "dimension": "AnomalyResults.windowStart",
          "granularity": "hour"
        }
      ],
      "filters": [
        {
          "member": "AnomalyResults.isAnomaly",
          "operator": "equals",
          "values": ["true"]
        }
      ]
    }
  }'
```

### GraphQL Query — KPI Summary

```graphql
query {
  cube(where: {}) {
    KpiSummary {
      totalAttacks
      failedLoginRate
      avgMttdMinutes
      avgMttrMinutes
      slaCompliance
    }
  }
}
```

**cURL equivalent:**

```bash
curl -X POST http://localhost:4000/cubejs-api/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-cubejs-api-secret" \
  -d '{
    "query": "{ cube(where: {}) { KpiSummary { totalAttacks failedLoginRate avgMttdMinutes avgMttrMinutes slaCompliance } } }"
  }'
```

### GraphQL Query — Attack Volume with Date Filter

```graphql
query {
  cube(
    where: {
      AttackVolumeByDay: {
        eventDate: { afterDate: "2024-01-01", beforeDate: "2024-01-31" }
      }
    }
  ) {
    AttackVolumeByDay {
      attackCount
      cumulativeAttackCount
      eventDate { day }
    }
  }
}
```

---

## Superset Integration

### Connection Architecture

Superset can connect to Cube.js in two ways:

1. **Cube.js SQL API (Recommended)** — Superset connects via a SQL interface that Cube.js exposes, making it transparent to Superset's SQL-based chart engine.

2. **Direct DuckDB (MVP fallback)** — Superset connects directly to the DuckDB file, bypassing the semantic layer. Used when Cube.js is not running.

### Configuring Superset to Use Cube.js SQL API

In Superset's database connection settings:

```
SQLAlchemy URI: cube://cube:4000/db
```

Or configure via the Superset init script (`docker/superset/init_superset.sh`):

```bash
superset set-database \
  --database-name "Cube.js Security Analytics" \
  --sqlalchemy-uri "cube://cube:4000/db"
```

### Configuring Direct DuckDB (MVP)

For MVP mode without Cube.js:

```
SQLAlchemy URI: duckdb:///data/security_analytics.duckdb
```

### Dashboard Data Flow

```
Superset Chart Request
  → Cube.js REST API (/cubejs-api/v1/load)
    → Cube.js generates optimized SQL
      → DuckDB executes query on Gold tables
        → Results returned through the chain
```

### Pre-Aggregations

Cube.js uses pre-aggregations to cache frequently queried data:

| Cube | Pre-Aggregation | Granularity | Refresh |
|------|----------------|-------------|---------|
| AttackVolumeByDay | `daily` | day | On query |
| HourlyEventSummary | `hourly` | hour | On query |
| SecurityEvents | `daily` | day (partitioned by month) | On query |

---

## Error Handling

### Invalid Measure/Dimension

**Request with undefined measure:**

```json
{
  "query": {
    "measures": ["KpiSummary.nonExistentMeasure"]
  }
}
```

**Response (HTTP 400):**

```json
{
  "error": "Error: KpiSummary.nonExistentMeasure not found. Available measures: KpiSummary.totalAttacks, KpiSummary.failedLoginRate, KpiSummary.avgMttdMinutes, KpiSummary.avgMttrMinutes, KpiSummary.slaCompliance"
}
```

### Missing Authorization

**Response (HTTP 403):**

```json
{
  "error": "Invalid token"
}
```

---

## Health Check

```bash
curl http://localhost:4000/readyz
```

**Response (HTTP 200):**

```json
{ "status": "ready" }
```

---

## Configuration Reference

| Environment Variable | Default | Description |
|---|---|---|
| `CUBEJS_DB_TYPE` | `duckdb` | Database driver type |
| `CUBEJS_DB_DUCKDB_DATABASE_PATH` | `/cube/data/security_analytics.duckdb` | Path to DuckDB file |
| `CUBEJS_API_SECRET` | `your-cubejs-api-secret` | Secret for JWT token generation |
| `CUBEJS_DEV_MODE` | `true` | Enable Playground UI at port 4000 |
| `CUBEJS_PORT` | `4000` | HTTP port for the API |

---

## Rate Limits and Performance

- Queries over datasets up to 100,000 records return within 5 seconds (Requirement 6.3)
- Pre-aggregations reduce response time for repeated queries
- Cube.js Playground available at `http://localhost:4000` in dev mode for interactive query building
