# Data Lineage

## Complete Data Flow

```
Mock Data Generator (Python)
  ├── Output: mock_data/security_events.jsonl
  └── Output: mock_data/security_events.parquet
        │
        ▼
DLT Pipeline (dlt library)
  ├── Valid records → security_bronze.security_events_resource
  └── Invalid records → security_bronze.dead_letter_events
        │
        ▼
dbt Staging (view)
  └── security_silver.stg_security_events
        │
        ▼
dbt Silver (incremental)
  └── security_silver.silver_events
      ├── Deduplication (ROW_NUMBER by event_id)
      ├── Validation (timestamp, IP, severity)
      ├── Standardization (lowercase/uppercase)
      └── Enrichment (+7 derived columns)
        │
        ├────────────────────────────────────┐
        ▼                                    ▼
dbt Gold (tables)                    ML Feature Engineering
  ├── kpi_summary                      └── 10 features per hourly window
  ├── attack_volume_by_day                   │
  ├── attack_volume_by_country               ▼
  └── hourly_event_summary            IsolationForest Training
        │                                    │
        │                                    ▼
        │                              Anomaly Scoring
        │                                    │
        │                                    ▼
        │                              security_gold.anomaly_results
        │                                    │
        ├────────────────────────────────────┘
        ▼
Cube.js Semantic Layer (REST/GraphQL)
        │
        ▼
Apache Superset (Dashboard)
```

## Table Dependencies

| Table | Depends On | Updated By |
|-------|-----------|------------|
| security_bronze.security_events_resource | mock_data/*.jsonl | DLT Pipeline |
| security_silver.stg_security_events | security_events_resource | dbt (view) |
| security_silver.silver_events | stg_security_events | dbt (incremental) |
| security_silver.kpi_summary | silver_events | dbt (table) |
| security_silver.attack_volume_by_day | silver_events | dbt (table) |
| security_silver.attack_volume_by_country | silver_events | dbt (table) |
| security_silver.hourly_event_summary | silver_events | dbt (table) |
| security_gold.anomaly_results | silver_events | ML Pipeline |
