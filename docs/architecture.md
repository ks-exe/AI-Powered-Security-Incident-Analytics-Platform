# System Architecture

## Overview

The Security Incident Analytics Platform implements a modern data engineering architecture with these layers:

1. **Data Generation** — Synthetic security events via Mock Data Generator
2. **Ingestion** — DLT pipeline loading to Bronze layer (DuckDB/Iceberg)
3. **Transformation** — dbt medallion architecture (Bronze → Silver → Gold)
4. **AI/ML** — IsolationForest anomaly detection on hourly feature vectors
5. **Semantic Layer** — Cube.js exposing Gold layer via REST/GraphQL
6. **Visualization** — Apache Superset interactive dashboards
7. **Orchestration** — Dagster pipeline scheduling and asset management
8. **Observability** — Structured JSON logging and health checks

## Component Interaction

```
Mock Generator → [JSONL/Parquet] → DLT Pipeline → [DuckDB Bronze]
    → dbt Silver (dedup + enrich) → dbt Gold (KPIs + aggregations)
    → ML Feature Extraction → IsolationForest → Anomaly Results
    → Cube.js Semantic Layer → Superset Dashboard
```

All components are orchestrated by Dagster with a daily schedule (02:00 UTC).

## Port Allocation

| Service | Port | Purpose |
|---------|------|---------|
| MinIO API | 9000 | Object storage |
| MinIO Console | 9001 | Storage management UI |
| Nessie | 19120 | Iceberg catalog |
| Dagster | 3000 | Pipeline monitoring |
| Cube.js | 4000 | Semantic layer API |
| Superset | 8088 | Dashboards |

## Data Storage

- **MVP**: Local DuckDB file at `data/security_analytics.duckdb`
- **Production**: MinIO object storage with Iceberg table format and Nessie catalog
