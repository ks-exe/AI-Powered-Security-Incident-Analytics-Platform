# Requirements Document — AI-Powered Security Incident Analytics Platform

## Introduction

The AI-Powered Security Incident Analytics Platform is a production-style portfolio project demonstrating modern data engineering, analytics engineering, orchestration, observability, data lake architecture, semantic layers, and AI-powered anomaly detection. The platform ingests mock security logs, stores them in a modern data lake (MinIO + Apache Iceberg + Nessie), transforms raw data through a medallion architecture (Bronze → Silver → Gold), computes security KPIs, exposes analytics through a semantic layer (Cube.js), visualizes dashboards (Apache Superset), orchestrates pipelines (Dagster), and detects anomalies using machine learning (scikit-learn IsolationForest).

### Architecture Review Summary

**MVP (Version 1):** Mock Generator → DLT → DuckDB/Parquet → dbt → Gold Tables → Superset (direct connection) → Dagster → IsolationForest
**Production Style (Version 2):** Mock Generator → DLT → Iceberg → MinIO → Nessie → DuckDB → dbt → Cube.js → Superset → Dagster → IsolationForest + Observability

**Rationale:** Version 1 removes MinIO/Nessie/Iceberg/Cube.js complexity to validate core data flow first. Version 2 layers in production infrastructure. The requirements below cover the full Version 2 scope with dependency annotations indicating MVP vs Production components.

### Dependency Map

```
[Phase 1] Mock_Data_Generator (no dependencies)
[Phase 2] Data_Lake Infrastructure (Docker)
[Phase 3] DLT_Pipeline (depends on: Mock_Data_Generator, Data_Lake)
[Phase 4] DBT_Layer Bronze→Silver (depends on: DLT_Pipeline)
[Phase 5] DBT_Layer Silver→Gold + KPIs (depends on: Silver Layer)
[Phase 6] Semantic_Layer (depends on: Gold Layer)
[Phase 7] Dashboard (depends on: Semantic_Layer)
[Phase 8] Orchestrator (depends on: all pipeline stages)
[Phase 9] Anomaly_Detector (depends on: Silver Layer)
[Phase 10] Observability (cross-cutting, incremental)
```

### Implementation Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Iceberg + Nessie + DuckDB integration immaturity | High — limited community examples | Start with DuckDB + Parquet in MVP; layer Iceberg in Phase 2 |
| Docker resource consumption (8+ containers) | Medium — student laptop constraints | Document minimum 16GB RAM; provide lite profile |
| Cube.js ↔ DuckDB connector compatibility | Medium — connector may lack features | Validate connector early; fallback to direct DuckDB queries |
| dbt-duckdb adapter limitations with Iceberg | Medium — adapter evolving rapidly | Pin adapter version; document known limitations |
| IsolationForest on small synthetic data | Low — model may not produce meaningful anomalies | Inject known anomaly patterns in mock data for validation |
| Superset Docker image size and startup time | Low — large image | Use slim image; document expected startup time |

---

## Glossary

- **Platform**: The AI-Powered Security Incident Analytics Platform system as a whole
- **Mock_Data_Generator**: The Python module responsible for generating synthetic security log events
- **Data_Lake**: The storage layer composed of MinIO object storage, Apache Iceberg table format, and Nessie catalog
- **DLT_Pipeline**: The data loading tool (dlt) pipeline that ingests raw security logs into the Data_Lake
- **DuckDB_Engine**: The DuckDB query engine used for analytical queries over Iceberg tables
- **DBT_Layer**: The dbt Core transformation layer implementing the medallion architecture
- **Bronze_Layer**: The raw ingestion layer storing unmodified security log events
- **Silver_Layer**: The cleaned and enriched layer with validated, deduplicated, and standardized events
- **Gold_Layer**: The business-level aggregation layer containing computed KPIs and analytical datasets
- **Semantic_Layer**: The Cube.js semantic layer exposing analytics through REST and GraphQL APIs
- **Dashboard**: The Apache Superset visualization layer displaying security KPI dashboards
- **Orchestrator**: The Dagster orchestration engine managing pipeline scheduling and dependencies
- **Anomaly_Detector**: The scikit-learn IsolationForest-based module for detecting anomalous security patterns
- **MTTD**: Mean Time To Detect — average time between event_time and detection_time
- **MTTR**: Mean Time To Respond — average time between detection_time and resolution_time
- **SLA_Compliance**: Percentage of incidents where MTTR ≤ SLA threshold (default: 4 hours)
- **Medallion_Architecture**: Data architecture pattern: Bronze (raw), Silver (cleaned), Gold (aggregated)
- **Iceberg_Table**: Apache Iceberg-formatted table stored in MinIO with schema evolution and time-travel
- **Nessie_Catalog**: Git-like catalog for Iceberg tables providing versioning and branching
- **Security_Event**: A single log record representing a security-relevant occurrence
- **KPI**: Key Performance Indicator — a quantifiable metric for security posture evaluation
- **Dead_Letter_Table**: A table storing malformed or rejected records for later inspection
- **Feature_Vector**: A numerical representation of a time window's security characteristics used for ML
- **Anomaly_Score**: A value between -1 (anomalous) and 1 (normal) assigned by IsolationForest
- **Health_Check**: An HTTP endpoint returning service status (healthy/unhealthy) and diagnostics
- **Idempotent_Operation**: An operation that produces the same result regardless of how many times it is executed

---

## Data Model Specification

### Security_Event Schema (Source)

| Column | Data Type | Nullable | Description | Example |
|--------|-----------|----------|-------------|---------|
| event_id | STRING (UUID) | No | Unique identifier for each event | "a1b2c3d4-e5f6-7890-abcd-ef1234567890" |
| event_time | TIMESTAMP | No | When the event occurred (UTC) | "2024-01-15T14:32:07Z" |
| username | STRING | No | User account associated with event | "john.smith" |
| src_ip | STRING (IPv4) | No | Source IP address | "192.168.1.105" |
| destination_ip | STRING (IPv4) | Yes | Destination IP address | "10.0.0.50" |
| hostname | STRING | No | Machine hostname | "WS-FINANCE-042" |
| event_type | STRING (ENUM) | No | Category of security event | "failed_login" |
| severity | STRING (ENUM) | No | Severity level: low, medium, high, critical | "high" |
| status | STRING | No | Outcome: success, failure, blocked, detected | "failure" |
| country | STRING (ISO 3166-1) | No | Country of origin for src_ip | "US" |
| operating_system | STRING | No | OS of source machine | "Windows 11" |
| department | STRING | No | Organizational department | "Finance" |

### Security_Event Schema (Silver Layer — Enriched)

| Column | Data Type | Nullable | Description | Example |
|--------|-----------|----------|-------------|---------|
| event_id | STRING (UUID) | No | Unique identifier (deduplicated) | "a1b2c3d4-..." |
| event_time | TIMESTAMP | No | Validated UTC timestamp | "2024-01-15T14:32:07Z" |
| detection_time | TIMESTAMP | Yes | Simulated time event was detected | "2024-01-15T14:35:22Z" |
| resolution_time | TIMESTAMP | Yes | Simulated time event was resolved | "2024-01-15T15:10:45Z" |
| username | STRING | No | Standardized username (lowercase) | "john.smith" |
| src_ip | STRING (IPv4) | No | Validated source IP | "192.168.1.105" |
| destination_ip | STRING (IPv4) | Yes | Validated destination IP | "10.0.0.50" |
| hostname | STRING | No | Standardized hostname (uppercase) | "WS-FINANCE-042" |
| event_type | STRING (ENUM) | No | Validated event category | "failed_login" |
| severity | STRING (ENUM) | No | Validated severity | "high" |
| severity_rank | INTEGER | No | Numeric severity: low=1, medium=2, high=3, critical=4 | 3 |
| status | STRING | No | Validated outcome | "failure" |
| country | STRING (ISO 3166-1) | No | Validated country code | "US" |
| operating_system | STRING | No | Standardized OS name | "Windows 11" |
| department | STRING | No | Standardized department name | "Finance" |
| hour_of_day | INTEGER | No | Derived: 0-23 | 14 |
| day_of_week | INTEGER | No | Derived: 1=Monday to 7=Sunday | 1 |
| is_business_hours | BOOLEAN | No | Derived: True if 09:00-17:00 local | true |
| is_internal_ip | BOOLEAN | No | Derived: True if src_ip is RFC1918 | true |
| is_attack_event | BOOLEAN | No | Derived: True if event_type is attack-related | false |
| _ingested_at | TIMESTAMP | No | Metadata: when record entered Bronze | "2024-01-15T15:00:00Z" |
| _source_file | STRING | No | Metadata: origin file path | "mock_data/batch_001.jsonl" |
| _batch_id | STRING | No | Metadata: unique batch identifier | "batch_20240115_001" |

### Additional Fields for MTTD/MTTR/SLA (Generated in Mock Data)

The Mock_Data_Generator SHALL simulate detection_time and resolution_time:
- **detection_time**: event_time + random(1min to 60min) for attack events; NULL for non-attack events
- **resolution_time**: detection_time + random(10min to 8hours) for attack events; NULL for non-attack events
- These fields enable MTTD, MTTR, and SLA_Compliance computation without external system dependencies

---

## Requirements

### Requirement 1: Mock Security Log Generation

**User Story:** As a data engineer, I want to generate realistic mock security log data with configurable volume and injected anomaly patterns, so that I can test the entire pipeline and validate anomaly detection without requiring real production security logs.

**Dependency:** None (entry point)
**Phase:** MVP + Production

#### Acceptance Criteria

1. WHEN the Mock_Data_Generator is invoked with a count parameter, THE Mock_Data_Generator SHALL produce the specified number of Security_Event records with a minimum supported count of 10,000 events and a maximum of 1,000,000 events
2. THE Mock_Data_Generator SHALL produce Security_Event records containing all required fields as defined in the Security_Event Schema including detection_time and resolution_time for attack events
3. WHEN generating event_type values, THE Mock_Data_Generator SHALL randomly assign one of: failed_login, successful_login, malware_alert, privilege_escalation, suspicious_ip_activity, vpn_login, account_lockout, brute_force_attempt — with configurable probability weights
4. THE Mock_Data_Generator SHALL generate event_time values distributed across a configurable time range (default: 30 days) with realistic temporal patterns including business-hour clustering (70% of events during 09:00-17:00 UTC) and attack burst simulation (3-5 burst windows per generated period)
5. THE Mock_Data_Generator SHALL assign severity values with default distribution: low=40%, medium=30%, high=20%, critical=10%
6. WHEN generating src_ip values, THE Mock_Data_Generator SHALL produce valid IPv4 addresses with 60% internal (RFC1918) and 40% external addresses
7. THE Mock_Data_Generator SHALL output data in JSON Lines format (.jsonl) and Parquet format (.parquet) to the mock_data/ directory
8. WHEN a seed parameter is provided, THE Mock_Data_Generator SHALL produce deterministic output for reproducibility
9. THE Mock_Data_Generator SHALL inject configurable anomaly patterns: a burst of 50+ failed_logins from a single IP within 5 minutes, privilege_escalation events outside business hours, and geographic anomalies (events from unusual countries)
10. THE Mock_Data_Generator SHALL generate realistic field correlations: internal IPs correlate with known departments, attack events correlate with higher severity, brute_force_attempt events correlate with account_lockout events

#### Implementation Notes
- Use Python Faker library for realistic usernames, hostnames
- Use numpy for statistical distributions
- Anomaly injection ensures IsolationForest has detectable patterns to learn
- Parquet output enables efficient DuckDB queries; JSONL enables streaming ingestion

### Requirement 2: Modern Data Lake Infrastructure

**User Story:** As a data engineer, I want a containerized data lake with object storage, table format, and catalog services, so that I can store and manage analytical data with schema evolution and versioning.

**Dependency:** None (infrastructure)
**Phase:** Production (MVP uses local DuckDB + Parquet files)

#### Acceptance Criteria

1. THE Platform SHALL provide a Docker Compose configuration that starts all services (MinIO, Nessie, Superset, Dagster, Cube.js) with a single `docker compose up` command
2. THE Platform SHALL provide a `docker-compose.lite.yml` profile that starts only MinIO and Nessie for development with reduced resource usage (under 4GB RAM)
3. WHEN Docker Compose is started, THE Data_Lake SHALL expose MinIO on port 9000 (API) and 9001 (console) with default credentials configurable via environment variables
4. WHEN Docker Compose is started, THE Data_Lake SHALL expose Nessie catalog on port 19120 with REST API access
5. THE Data_Lake SHALL create MinIO buckets on startup: `bronze-layer`, `silver-layer`, `gold-layer`, `raw-data`
6. THE Data_Lake SHALL register all Iceberg tables in the Nessie_Catalog with namespace organization matching the medallion layers
7. WHEN a schema change is applied, THE Data_Lake SHALL support schema evolution on Iceberg tables without requiring data rewrite
8. IF a Docker service fails to start, THEN THE Platform SHALL log a descriptive error message and the `docker compose up` command SHALL exit with a non-zero status code
9. THE Platform SHALL include a `scripts/setup.sh` script that validates prerequisites (Docker, Docker Compose, minimum RAM) before starting services
10. THE Platform SHALL document minimum system requirements: 16GB RAM, 20GB disk space, Docker Engine 24+, Docker Compose v2+

#### Implementation Notes
- Use Docker healthchecks for service readiness
- MinIO initialization via mc (MinIO Client) in an init container
- Nessie uses in-memory store for development (RocksDB for production profile)
- All ports configurable via .env file

### Requirement 3: DLT Ingestion Pipeline

**User Story:** As a data engineer, I want an automated ingestion pipeline that loads raw security logs into the data lake, so that raw data is reliably persisted in the Bronze layer for downstream processing.

**Dependency:** Requirement 1 (Mock_Data_Generator), Requirement 2 (Data_Lake)
**Phase:** MVP (DuckDB/Parquet) + Production (Iceberg/MinIO)

#### Acceptance Criteria

1. WHEN the DLT_Pipeline is executed, THE DLT_Pipeline SHALL read Security_Event records from JSON Lines files in mock_data/ and write them to the Bronze_Layer as DuckDB tables (MVP) or Iceberg tables (Production)
2. THE DLT_Pipeline SHALL preserve all original fields from the source data without modification in the Bronze_Layer
3. WHEN ingesting data, THE DLT_Pipeline SHALL add metadata columns: _ingested_at (UTC timestamp of ingestion), _source_file (origin file path), _batch_id (unique batch identifier in format batch_YYYYMMDD_NNN)
4. IF the DLT_Pipeline encounters a record with missing required fields (event_id, event_time, event_type), THEN THE DLT_Pipeline SHALL route the record to a dead_letter_events table and continue processing valid records
5. WHEN the DLT_Pipeline completes a batch, THE DLT_Pipeline SHALL log: records_ingested (integer), records_rejected (integer), elapsed_seconds (float), records_per_second (float)
6. THE DLT_Pipeline SHALL support incremental loading by tracking the last processed file position, avoiding reprocessing of previously ingested data
7. THE DLT_Pipeline SHALL be idempotent: re-running the pipeline with the same input data SHALL NOT create duplicate records in the Bronze_Layer
8. WHEN the DLT_Pipeline processes 10,000 records, THE DLT_Pipeline SHALL complete ingestion within 60 seconds on a standard development machine

#### Implementation Notes
- dlt resource/source pattern for modular pipeline definition
- Use dlt's built-in state management for incremental loading
- DuckDB destination for MVP; switch to filesystem + Iceberg for Production
- Dead letter routing via dlt's error handling hooks

### Requirement 4: dbt Transformation Layer (Medallion Architecture)

**User Story:** As an analytics engineer, I want a structured transformation layer that progressively refines raw security data into analytical datasets, so that downstream consumers receive clean, enriched, and aggregated data.

**Dependency:** Requirement 3 (DLT_Pipeline populates Bronze)
**Phase:** MVP + Production

#### Acceptance Criteria

1. THE DBT_Layer SHALL implement a Bronze → Silver → Gold medallion architecture with explicit model dependencies defined via dbt ref() functions
2. WHEN transforming Bronze to Silver, THE DBT_Layer SHALL deduplicate records based on event_id keeping the record with the latest _ingested_at timestamp
3. WHEN transforming Bronze to Silver, THE DBT_Layer SHALL validate and cast: event_time to TIMESTAMP (rejecting records with unparseable timestamps), severity to lowercase enum (low, medium, high, critical), src_ip to validated IPv4 format (rejecting malformed IPs)
4. WHEN transforming Bronze to Silver, THE DBT_Layer SHALL enrich records with derived fields: hour_of_day (INTEGER 0-23), day_of_week (INTEGER 1-7), is_business_hours (BOOLEAN, true if 09:00-17:00 UTC), is_internal_ip (BOOLEAN, true if RFC1918), severity_rank (INTEGER 1-4), is_attack_event (BOOLEAN)
5. WHEN transforming Silver to Gold, THE DBT_Layer SHALL compute all KPIs defined in Requirement 5 as materialized tables
6. THE DBT_Layer SHALL include dbt tests: uniqueness of event_id in Silver, not-null on all non-nullable fields, accepted_values for event_type (8 types) and severity (4 levels), relationships between Gold and Silver tables
7. THE DBT_Layer SHALL use DuckDB as the query engine via the dbt-duckdb adapter with profiles.yml configured for local development
8. THE DBT_Layer SHALL generate documentation via `dbt docs generate` including a DAG visualization and column-level descriptions
9. WHEN `dbt build` is executed, THE DBT_Layer SHALL complete all models and tests within 120 seconds for a 10,000-record Bronze dataset
10. THE DBT_Layer SHALL use dbt sources to define the Bronze layer tables, enabling source freshness checks

#### Implementation Notes
- Models organized: models/bronze/, models/silver/, models/gold/
- Use dbt macros for reusable transformation logic (IP validation, severity mapping)
- Incremental models for Silver layer (append-only with dedup)
- Full refresh for Gold layer (aggregations recomputed)
- schema.yml files for all models with column descriptions

### Requirement 5: Security KPI Computation

**User Story:** As a security analyst, I want pre-computed security KPIs available in the Gold layer, so that I can monitor organizational security posture through standardized metrics.

**Dependency:** Requirement 4 (Silver Layer must exist)
**Phase:** MVP + Production

#### Acceptance Criteria

1. THE Gold_Layer SHALL contain a `total_attacks` metric computed as COUNT(*) FROM silver_events WHERE event_type IN ('malware_alert', 'privilege_escalation', 'suspicious_ip_activity', 'brute_force_attempt')
2. THE Gold_Layer SHALL contain a `failed_login_rate` metric computed as COUNT(failed_login) / COUNT(failed_login + successful_login) expressed as a decimal between 0.0 and 1.0
3. THE Gold_Layer SHALL contain an `avg_mttd` metric computed as AVG(detection_time - event_time) for records WHERE detection_time IS NOT NULL, expressed in minutes
4. THE Gold_Layer SHALL contain an `avg_mttr` metric computed as AVG(resolution_time - detection_time) for records WHERE resolution_time IS NOT NULL, expressed in minutes
5. THE Gold_Layer SHALL contain an `sla_compliance` metric computed as COUNT(records WHERE MTTR <= 240 minutes) / COUNT(records WHERE resolution_time IS NOT NULL), expressed as a decimal between 0.0 and 1.0
6. THE Gold_Layer SHALL contain an `attack_volume_by_day` table with columns: event_date (DATE), attack_count (INTEGER), cumulative_attack_count (INTEGER)
7. THE Gold_Layer SHALL contain an `attack_volume_by_country` table with columns: country (STRING), attack_count (INTEGER), percentage_of_total (DECIMAL)
8. THE Gold_Layer SHALL contain a `kpi_summary` table aggregating all scalar KPIs into a single row with computed_at timestamp for dashboard consumption
9. THE Gold_Layer SHALL contain an `hourly_event_summary` table with columns: event_hour (TIMESTAMP truncated to hour), event_type, event_count, unique_ips, unique_users — used as input for Anomaly_Detector

#### KPI Definitions

| KPI | Business Definition | SQL Formula | Source | Update Frequency |
|-----|-------------------|-------------|--------|-----------------|
| total_attacks | Total security attack events detected | `COUNT(*) WHERE is_attack_event = true` | silver_events | Per pipeline run |
| failed_login_rate | Ratio of failed to total login attempts | `SUM(CASE WHEN event_type='failed_login' THEN 1 END) / SUM(CASE WHEN event_type IN ('failed_login','successful_login') THEN 1 END)` | silver_events | Per pipeline run |
| avg_mttd | Average minutes from attack to detection | `AVG(EXTRACT(EPOCH FROM detection_time - event_time)/60) WHERE detection_time IS NOT NULL` | silver_events | Per pipeline run |
| avg_mttr | Average minutes from detection to resolution | `AVG(EXTRACT(EPOCH FROM resolution_time - detection_time)/60) WHERE resolution_time IS NOT NULL` | silver_events | Per pipeline run |
| sla_compliance | Percentage of incidents resolved within SLA | `COUNT(*) FILTER(WHERE EXTRACT(EPOCH FROM resolution_time-detection_time)/60 <= 240) / COUNT(*) FILTER(WHERE resolution_time IS NOT NULL)` | silver_events | Per pipeline run |
| attack_volume_by_day | Daily attack event counts | `COUNT(*) WHERE is_attack_event GROUP BY DATE(event_time)` | silver_events | Per pipeline run |
| attack_volume_by_country | Attack counts by source country | `COUNT(*) WHERE is_attack_event GROUP BY country` | silver_events | Per pipeline run |

#### Additional Recommended KPIs

| KPI | Business Definition | Rationale |
|-----|-------------------|-----------|
| top_targeted_users | Users with most attack events | Identifies compromised accounts |
| attack_severity_distribution | Breakdown by severity level | Shows threat landscape composition |
| repeat_offender_ips | IPs with 5+ attack events | Identifies persistent threats |
| department_risk_score | Weighted attack count per department | Prioritizes security investment |
| login_failure_by_hour | Failed logins per hour of day | Identifies brute force timing patterns |
| geographic_anomaly_score | Countries with unusual event spikes | Detects geographic-based attacks |

#### Implementation Notes
- All KPIs materialized as dbt models in models/gold/
- kpi_summary is a single-row table for easy dashboard binding
- hourly_event_summary feeds the Anomaly_Detector feature engineering

### Requirement 6: Cube.js Semantic Layer

**User Story:** As a platform consumer, I want a semantic layer that exposes security KPIs through standardized APIs, so that dashboards and applications can query analytics without direct database access.

**Dependency:** Requirement 5 (Gold Layer tables must exist)
**Phase:** Production (MVP connects Superset directly to DuckDB)

#### Acceptance Criteria

1. THE Semantic_Layer SHALL expose all Gold_Layer KPIs through REST API endpoints at `/cubejs-api/v1/load`
2. THE Semantic_Layer SHALL expose all Gold_Layer KPIs through a GraphQL API endpoint at `/cubejs-api/graphql`
3. WHEN a query is submitted to the Semantic_Layer, THE Semantic_Layer SHALL return results within 5 seconds for queries over datasets up to 100,000 records
4. THE Semantic_Layer SHALL define Cube.js data models (cubes) for: SecurityEvents, KpiSummary, AttackVolumeByDay, AttackVolumeByCountry, HourlyEventSummary, AnomalyResults
5. THE Semantic_Layer SHALL support time-dimension filtering on event_time allowing queries by: date range, hour of day, day of week, month
6. THE Semantic_Layer SHALL support dimension filtering on: event_type, severity, country, department, is_anomaly
7. THE Semantic_Layer SHALL run as a Docker container on port 4000 integrated with the Platform Docker Compose configuration
8. IF the Semantic_Layer receives a query referencing an undefined measure or dimension, THEN THE Semantic_Layer SHALL return HTTP 400 with a JSON error body containing available measures and dimensions
9. THE Semantic_Layer SHALL connect to DuckDB as its data source using the DuckDB driver
10. THE Semantic_Layer SHALL define pre-aggregations for frequently queried KPIs to improve response time

#### Implementation Notes
- Cube.js schema files in cube/schema/ directory
- Use DuckDB driver (cube-duckdb-driver)
- Pre-aggregations for daily/hourly rollups
- CORS configured for Superset integration
- API token authentication for production profile

### Requirement 7: Apache Superset Dashboard

**User Story:** As a security analyst, I want interactive dashboards visualizing security KPIs, so that I can monitor threats, identify trends, and communicate security posture to stakeholders.

**Dependency:** Requirement 6 (Semantic_Layer) or Requirement 5 (Gold Layer for MVP direct connection)
**Phase:** MVP (direct DuckDB) + Production (via Cube.js)

#### Acceptance Criteria

1. THE Dashboard SHALL display a Security Overview page containing KPI cards: total_attacks (integer), failed_login_rate (percentage with 1 decimal), avg_mttd (minutes), avg_mttr (minutes), sla_compliance (percentage)
2. THE Dashboard SHALL display a time-series line chart showing attack_volume_by_day over the full generated time range with date axis
3. THE Dashboard SHALL display a geographic breakdown using a world map or horizontal bar chart showing attack_volume_by_country (top 10 countries)
4. THE Dashboard SHALL display a bar chart showing event count breakdown by event_type (all 8 types)
5. THE Dashboard SHALL display a donut chart showing severity distribution (low, medium, high, critical) with percentage labels
6. THE Dashboard SHALL display an anomaly timeline chart showing anomaly_score over time with a threshold line at -0.5
7. THE Dashboard SHALL connect to the Semantic_Layer (Production) or directly to DuckDB (MVP) as its data source
8. THE Dashboard SHALL run as a Docker container on port 8088 integrated with the Platform Docker Compose configuration
9. WHEN a dashboard filter is applied (date range, event_type, severity, country), THE Dashboard SHALL update all visualizations within 3 seconds
10. THE Dashboard SHALL be exportable as a JSON configuration file stored in dashboards/ for version control and reproducibility

#### Dashboard Layout Specification

```
┌─────────────────────────────────────────────────────────────┐
│ Security Incident Analytics Platform — Overview Dashboard    │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│ Total    │ Failed   │ Avg MTTD │ Avg MTTR │ SLA Compliance │
│ Attacks  │ Login %  │ (min)    │ (min)    │ (%)            │
├──────────┴──────────┴──────────┴──────────┴────────────────┤
│ [Attack Volume by Day — Time Series Line Chart]             │
├─────────────────────────────┬───────────────────────────────┤
│ [Events by Type — Bar]      │ [Severity Distribution—Donut] │
├─────────────────────────────┴───────────────────────────────┤
│ [Attack Volume by Country — Horizontal Bar / Map]           │
├─────────────────────────────────────────────────────────────┤
│ [Anomaly Score Timeline — Line Chart with Threshold]        │
└─────────────────────────────────────────────────────────────┘
```

#### Implementation Notes
- Use Superset's dashboard export/import for reproducibility
- Store dashboard JSON in dashboards/security_overview.json
- Configure database connection via Superset CLI or API on startup
- Use init container to bootstrap Superset admin user and database connection

### Requirement 8: Dagster Orchestration

**User Story:** As a data engineer, I want automated pipeline orchestration with scheduling, dependency management, and monitoring, so that data flows reliably from ingestion through transformation to serving.

**Dependency:** Requirements 1, 3, 4, 5, 9 (all pipeline stages)
**Phase:** Production (MVP runs stages manually via scripts)

#### Acceptance Criteria

1. THE Orchestrator SHALL define a Dagster job named `security_analytics_pipeline` that executes: Mock_Data_Generator → DLT_Pipeline → DBT_Layer (Bronze→Silver→Gold) → Anomaly_Detector
2. THE Orchestrator SHALL define individual software-defined assets for: raw_security_events, bronze_events, silver_events, gold_kpi_summary, gold_attack_by_day, gold_attack_by_country, gold_hourly_summary, anomaly_results
3. WHEN a pipeline run is triggered, THE Orchestrator SHALL execute stages in dependency order, waiting for upstream asset materialization before starting downstream stages
4. THE Orchestrator SHALL provide Dagster Dagit web UI on port 3000 for monitoring pipeline runs, viewing logs, and triggering manual executions
5. IF a pipeline stage fails, THEN THE Orchestrator SHALL mark the run as failed, log the error with stage name and stack trace, and halt downstream execution without affecting previously materialized assets
6. THE Orchestrator SHALL support scheduled execution via a Dagster schedule with configurable cron expression (default: `0 2 * * *` — daily at 02:00 UTC)
7. THE Orchestrator SHALL run as a Docker container (dagster-webserver + dagster-daemon) integrated with the Platform Docker Compose configuration
8. THE Orchestrator SHALL track asset lineage showing upstream/downstream dependencies in the Dagit asset graph
9. THE Orchestrator SHALL support manual asset materialization allowing individual assets to be refreshed independently
10. WHEN a pipeline run completes successfully, THE Orchestrator SHALL emit a structured log entry with: run_id, duration_seconds, assets_materialized (list), records_processed (integer)

#### Implementation Notes
- Use Dagster's @asset decorator for software-defined assets
- Use Dagster's @job and @op for the full pipeline job
- Dagster resources for DuckDB connection, dbt integration (dagster-dbt)
- Dagster sensors for file-based triggering (detect new mock data files)
- Store Dagster workspace in dagster/ directory with workspace.yaml

### Requirement 9: AI Anomaly Detection

**User Story:** As a security analyst, I want automated anomaly detection on security event patterns, so that unusual activity is flagged for investigation without manual threshold tuning.

**Dependency:** Requirement 4 (Silver Layer), Requirement 5 (hourly_event_summary)
**Phase:** MVP + Production

#### Acceptance Criteria

1. THE Anomaly_Detector SHALL train a scikit-learn IsolationForest model on feature vectors derived from the Gold_Layer hourly_event_summary table
2. THE Anomaly_Detector SHALL extract the following features per hourly time window: total_event_count, unique_src_ips, unique_users, failed_login_count, failed_login_ratio, attack_event_count, avg_severity_rank, critical_event_count, unique_countries, events_outside_business_hours_ratio
3. WHEN the trained model scores new data, THE Anomaly_Detector SHALL assign an anomaly_score between -1 (most anomalous) and 1 (most normal) to each hourly time window
4. WHEN an anomaly_score falls below a configurable threshold (default: -0.5), THE Anomaly_Detector SHALL flag the time window as anomalous (is_anomaly = true)
5. THE Anomaly_Detector SHALL persist results to a Gold_Layer table `anomaly_results` with columns: window_start (TIMESTAMP), window_end (TIMESTAMP), anomaly_score (FLOAT), is_anomaly (BOOLEAN), total_event_count (INTEGER), top_contributing_feature (STRING), model_version (STRING)
6. THE Anomaly_Detector SHALL log model metrics after training: contamination_parameter, n_estimators, n_samples_trained, n_anomalies_detected, anomaly_percentage, training_duration_seconds
7. WHEN the Anomaly_Detector is retrained, THE Anomaly_Detector SHALL save the model artifact as a joblib file with naming convention: `models/isolation_forest_v{YYYYMMDD_HHMMSS}.joblib`
8. THE Anomaly_Detector SHALL use IsolationForest with parameters: n_estimators=100, contamination=0.05, random_state=42 (all configurable)
9. THE Anomaly_Detector SHALL compute feature importance using permutation importance and store the top 3 contributing features for each anomalous window
10. THE Anomaly_Detector SHALL validate model quality by checking that anomaly_percentage is between 1% and 15% of total windows (alerting if outside this range indicates poor model fit)

#### AI Layer Specification

**Model Choice Rationale:**
- IsolationForest is appropriate for unsupervised anomaly detection on tabular time-series features
- No labeled data required (matches the mock data scenario)
- Computationally efficient for the dataset size (720 hourly windows per 30-day period)
- Interpretable anomaly scores

**Training Strategy:**
- Train on full historical dataset (all hourly windows)
- contamination parameter set to expected anomaly rate (5% default, matching injected anomaly rate)
- No train/test split needed for unsupervised detection (evaluate by checking injected anomalies are detected)

**Retraining Strategy:**
- Retrain on each full pipeline run (dataset is small enough)
- Version models with timestamps
- Keep last 5 model versions for comparison

**Evaluation Strategy:**
- Precision: What percentage of flagged windows contain injected anomaly patterns
- Recall: What percentage of injected anomaly windows are flagged
- Log both metrics; target precision > 0.7 and recall > 0.6 on injected anomalies

#### Implementation Notes
- Feature engineering in ml_detection/features.py
- Model training in ml_detection/train.py
- Model inference in ml_detection/predict.py
- Configuration in ml_detection/config.yaml
- Use pandas for feature engineering, scikit-learn for model

### Requirement 10: Observability and Monitoring

**User Story:** As a platform operator, I want comprehensive observability across all platform components, so that I can detect failures, diagnose performance issues, and ensure pipeline reliability.

**Dependency:** Cross-cutting (applies to all components)
**Phase:** Incremental (basic logging in MVP, full observability in Production)

#### Acceptance Criteria

1. THE Platform SHALL implement structured logging (JSON format) across all Python components with fields: timestamp (ISO8601), level (DEBUG/INFO/WARNING/ERROR), component (string), message (string), context (object with run_id, batch_id where applicable)
2. THE Platform SHALL use Python's standard logging module with a custom JSON formatter configured in a shared logging utility module
3. THE Platform SHALL track pipeline execution metrics per run: total_duration_seconds, records_ingested, records_transformed, records_rejected, stages_completed, stages_failed
4. WHEN a pipeline stage exceeds a configurable duration threshold (default: 300 seconds), THE Platform SHALL emit a WARNING log with stage_name, elapsed_seconds, and threshold_seconds
5. THE Platform SHALL expose HTTP health check endpoints for each containerized service: GET /health returning JSON `{"status": "healthy"|"unhealthy", "service": "<name>", "uptime_seconds": <int>}`
6. IF a service health check fails, THEN THE Platform SHALL log the failure with service_name, endpoint, error_message, and consecutive_failure_count
7. THE Platform SHALL provide a `scripts/health_check.sh` script that queries all service health endpoints and reports overall platform status
8. THE Platform SHALL write pipeline run summaries to a `logs/pipeline_runs.jsonl` file for historical analysis
9. THE Platform SHALL implement retry logic for transient failures: 3 retries with exponential backoff (1s, 2s, 4s) for database connections and file I/O operations
10. THE Platform SHALL document a log aggregation approach using Docker Compose logging drivers with instructions for connecting to ELK or Loki (documentation only, not implemented)

#### Implementation Notes
- Shared logging config in scripts/logging_config.py
- Health check endpoints added to Dagster webserver, Cube.js, custom services
- Pipeline metrics stored in DuckDB pipeline_metrics table for self-monitoring
- Retry decorator pattern for transient failure handling

### Requirement 11: Data Lineage Tracking

**User Story:** As a data engineer, I want end-to-end data lineage visibility, so that I can trace any analytical result back to its source data and understand transformation dependencies.

**Dependency:** Requirements 4, 8 (dbt DAG + Dagster asset graph)
**Phase:** MVP (dbt docs) + Production (Dagster asset lineage)

#### Acceptance Criteria

1. THE Platform SHALL document the complete data lineage in docs/data_lineage.md showing: Mock_Data_Generator → Bronze (raw_security_events) → Silver (silver_events) → Gold (kpi_summary, attack_by_day, attack_by_country, hourly_summary) → anomaly_results → Semantic_Layer → Dashboard
2. THE DBT_Layer SHALL generate a lineage graph via `dbt docs generate` showing all model dependencies with column-level lineage where supported
3. THE Orchestrator SHALL display asset dependencies in Dagit's asset graph showing upstream/downstream relationships
4. WHEN a Gold_Layer KPI is queried, THE Platform SHALL provide documentation in docs/ tracing the KPI computation back through Silver transformations to Bronze source fields
5. THE Platform SHALL include a docs/data_dictionary.md file documenting every table, column, data type, and business meaning across all layers

#### Implementation Notes
- dbt docs serve for interactive DAG exploration
- Dagster asset graph provides runtime lineage
- Manual documentation in docs/ for business context
- Consider OpenLineage integration as future enhancement

### Requirement 12: Production Readiness

**User Story:** As a developer, I want the platform to follow production-grade practices, so that the project demonstrates professional engineering standards suitable for a portfolio.

**Dependency:** All requirements
**Phase:** Incremental throughout

#### Acceptance Criteria

1. THE Platform SHALL include a README.md documenting: project overview, architecture diagram (Mermaid or ASCII), technology stack with version numbers, prerequisites, quick-start guide (under 5 commands to running state), project structure explanation, and links to detailed docs
2. THE Platform SHALL include a pyproject.toml with pinned Python dependency versions and dependency groups (core, dev, test, ml)
3. THE Platform SHALL include a .gitignore file excluding: mock_data/*.parquet, mock_data/*.jsonl, *.duckdb, .env, __pycache__/, venv/, docker volumes, .DS_Store, IDE files
4. THE Platform SHALL include unit tests in tests/unit/ for: Mock_Data_Generator (schema validation, deterministic seeding, field ranges), feature engineering (correct feature computation), KPI calculations (known-input/known-output)
5. THE Platform SHALL include integration tests in tests/integration/ for: DLT_Pipeline (end-to-end ingestion verification), dbt models (run and test), anomaly detection (train and predict cycle)
6. THE Platform SHALL organize source code following the defined project structure with __init__.py files and clear module boundaries
7. THE Platform SHALL include configuration management via: .env file for Docker service configuration, config.yaml files for Python component configuration, environment variable overrides documented in README
8. THE Platform SHALL include docs/ directory containing: architecture.md, data_lineage.md, data_dictionary.md, setup_guide.md, troubleshooting.md
9. THE Platform SHALL include a Makefile with targets: setup, generate-data, ingest, transform, detect-anomalies, run-pipeline, test, lint, docs, docker-up, docker-down, clean
10. THE Platform SHALL pass linting with ruff (Python) and validate all dbt models with `dbt test` as part of CI-ready test suite

#### Implementation Notes
- Makefile provides single-command operations for all pipeline stages
- pyproject.toml with [tool.ruff] configuration
- pytest as test runner with conftest.py for shared fixtures
- GitHub Actions workflow file (not executed, but included for portfolio demonstration)

---

## Non-Functional Requirements

### NFR 1: Performance

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Mock data generation (10K events) | < 10 seconds | Timer in generator script |
| DLT ingestion (10K records) | < 60 seconds | Pipeline completion log |
| dbt build (full refresh, 10K records) | < 120 seconds | dbt run duration |
| Cube.js query response (standard KPI) | < 5 seconds | API response time |
| Superset dashboard load | < 10 seconds | Browser network tab |
| Anomaly detection (train + predict) | < 30 seconds | Script timer |
| Full pipeline end-to-end (10K records) | < 5 minutes | Dagster run duration |

### NFR 2: Reliability

| Aspect | Requirement |
|--------|-------------|
| Retry strategy | 3 retries with exponential backoff (1s, 2s, 4s) for transient failures |
| Failure recovery | Failed pipeline stages do not corrupt previously materialized data |
| Idempotency | All pipeline stages produce identical results when re-run with same input |
| Data integrity | No data loss between layers; dead letter table captures all rejected records |
| Service recovery | Docker containers auto-restart on failure (restart: unless-stopped) |

### NFR 3: Maintainability

| Aspect | Requirement |
|--------|-------------|
| Modular architecture | Each component independently testable and replaceable |
| Configuration | All magic numbers externalized to config files or environment variables |
| Code organization | Clear separation: one directory per component, shared utilities in scripts/ |
| Documentation | Every public function has a docstring; every module has a module-level docstring |
| Dependency management | All dependencies pinned; no floating version ranges |

### NFR 4: Security

| Aspect | Requirement |
|--------|-------------|
| Secrets management | All credentials in .env file (gitignored); never hardcoded in source |
| Default credentials | Docker services use configurable credentials with documented defaults |
| Access controls | Superset requires authentication (admin user bootstrapped on startup) |
| Network isolation | Docker services communicate on internal network; only UI ports exposed to host |
| Input validation | All external inputs validated before processing (file paths, parameters) |

### NFR 5: Testing Strategy

| Level | Scope | Tools | Coverage Target |
|-------|-------|-------|----------------|
| Unit tests | Mock generator, feature engineering, KPI logic | pytest | Core logic functions |
| Integration tests | DLT pipeline, dbt models, anomaly detection | pytest + dbt test | End-to-end data flow |
| Data quality tests | Schema validation, value ranges, referential integrity | dbt tests + Great Expectations patterns | All Silver/Gold tables |
| Smoke tests | Docker services start and respond to health checks | scripts/health_check.sh | All containerized services |

---

## Project Roadmap

### Sprint 1: Project Foundation + Mock Data Generation (Days 1-3)

**Goals:** Initialize project structure, implement mock data generator with anomaly injection
**Deliverables:**
- Project directory structure with all placeholder files
- pyproject.toml with core dependencies
- Makefile with initial targets
- Mock data generator producing 10K+ events in JSONL and Parquet
- Unit tests for mock data generator
- README.md with project overview

**Files to Create:**
- pyproject.toml, Makefile, .gitignore, README.md
- mock_data/__init__.py, mock_data/generator.py, mock_data/config.yaml
- tests/unit/test_generator.py
- scripts/logging_config.py

**Success Criteria:** `make generate-data` produces valid 10K-event dataset; `make test` passes all unit tests
**Testing Criteria:** Deterministic output with seed, all fields present, correct distributions


### Sprint 2: DLT Ingestion + Bronze Layer (Days 4-6)

**Goals:** Implement DLT pipeline loading mock data into DuckDB Bronze layer
**Deliverables:**
- DLT pipeline with source and resource definitions
- Bronze layer table in DuckDB with metadata columns
- Dead letter table for rejected records
- Incremental loading support
- Integration test for ingestion

**Files to Create:**
- dlt_pipeline/__init__.py, dlt_pipeline/pipeline.py, dlt_pipeline/sources.py
- dlt_pipeline/config.yaml
- tests/integration/test_ingestion.py

**Success Criteria:** `make ingest` loads all mock data into DuckDB; dead letter table captures malformed records; re-running does not duplicate data
**Testing Criteria:** Record count matches source, metadata columns populated, idempotent re-run

### Sprint 3: dbt Silver Layer (Days 7-10)

**Goals:** Implement dbt transformations from Bronze to Silver with data quality tests
**Deliverables:**
- dbt project with profiles.yml for DuckDB
- Silver model with deduplication, validation, enrichment
- dbt tests for data quality
- dbt documentation

**Files to Create:**
- dbt_project/dbt_project.yml, dbt_project/profiles.yml
- dbt_project/models/staging/stg_security_events.sql
- dbt_project/models/silver/silver_events.sql
- dbt_project/models/silver/schema.yml
- dbt_project/macros/validate_ip.sql, dbt_project/macros/severity_rank.sql
- tests/integration/test_dbt_models.py

**Success Criteria:** `make transform` runs dbt build successfully; all dbt tests pass; Silver table has enriched columns
**Testing Criteria:** Deduplication verified, derived fields correct, data quality tests pass

### Sprint 4: dbt Gold Layer + KPIs (Days 11-13)

**Goals:** Implement Gold layer KPI models and summary tables
**Deliverables:**
- Gold layer dbt models for all 7+ KPIs
- kpi_summary single-row table
- hourly_event_summary for ML input
- dbt tests for Gold layer
- KPI validation tests

**Files to Create:**
- dbt_project/models/gold/kpi_summary.sql
- dbt_project/models/gold/attack_volume_by_day.sql
- dbt_project/models/gold/attack_volume_by_country.sql
- dbt_project/models/gold/hourly_event_summary.sql
- dbt_project/models/gold/schema.yml
- tests/unit/test_kpi_calculations.py

**Success Criteria:** All Gold models materialize; KPI values are within expected ranges for mock data; dbt docs generate shows complete DAG
**Testing Criteria:** KPI formulas validated against manual calculation on known subset

### Sprint 5: Apache Superset Dashboard (Days 14-17)

**Goals:** Deploy Superset via Docker, create security overview dashboard
**Deliverables:**
- Docker Compose service for Superset
- Database connection to DuckDB (or Cube.js in Production)
- Security Overview dashboard with all specified charts
- Dashboard export JSON for version control

**Files to Create:**
- docker/docker-compose.yml (Superset service)
- docker/superset/superset_config.py
- docker/superset/init_superset.sh
- dashboards/security_overview.json

**Success Criteria:** `docker compose up superset` starts Superset; dashboard displays all KPI visualizations; filters work correctly
**Testing Criteria:** All charts render with data; filter interactions update all charts


### Sprint 6: Cube.js Semantic Layer (Days 18-20)

**Goals:** Deploy Cube.js with data models exposing Gold layer through APIs
**Deliverables:**
- Docker Compose service for Cube.js
- Cube.js schema files for all Gold tables
- REST and GraphQL API endpoints
- Pre-aggregations for common queries
- API documentation

**Files to Create:**
- docker/docker-compose.yml (Cube.js service addition)
- cube/schema/SecurityEvents.js
- cube/schema/KpiSummary.js
- cube/schema/AttackVolume.js
- cube/schema/AnomalyResults.js
- cube/.env
- docs/api_specification.md

**Success Criteria:** Cube.js playground accessible; REST API returns KPI data; GraphQL queries work; response time < 5s
**Testing Criteria:** All measures and dimensions queryable; time filters work; error responses correct

### Sprint 7: Dagster Orchestration (Days 21-24)

**Goals:** Implement Dagster orchestration with software-defined assets and scheduling
**Deliverables:**
- Dagster project with workspace configuration
- Software-defined assets for each pipeline stage
- Full pipeline job with dependency ordering
- Schedule configuration
- Docker Compose integration

**Files to Create:**
- dagster/workspace.yaml
- dagster/__init__.py, dagster/assets.py, dagster/jobs.py
- dagster/schedules.py, dagster/resources.py
- dagster/Dockerfile
- docker/docker-compose.yml (Dagster services addition)

**Success Criteria:** Dagit UI accessible; full pipeline job executes successfully; asset graph shows correct dependencies; schedule configured
**Testing Criteria:** Individual assets materializable; failure in one stage halts downstream; logs captured

### Sprint 8: AI Anomaly Detection (Days 25-28)

**Goals:** Implement IsolationForest anomaly detection with feature engineering and model versioning
**Deliverables:**
- Feature engineering module
- Model training module
- Model inference module
- Results persistence to Gold layer
- Model versioning
- Evaluation metrics

**Files to Create:**
- ml_detection/__init__.py, ml_detection/features.py
- ml_detection/train.py, ml_detection/predict.py
- ml_detection/evaluate.py, ml_detection/config.yaml
- models/.gitkeep
- tests/unit/test_features.py
- tests/integration/test_anomaly_detection.py

**Success Criteria:** `make detect-anomalies` trains model and produces anomaly results; injected anomalies detected with precision > 0.7; model artifact saved with version
**Testing Criteria:** Feature vectors computed correctly; model trains without error; anomaly percentage within 1-15% range

### Sprint 9: Data Lake Integration — Iceberg + Nessie + MinIO (Days 29-32)

**Goals:** Layer production data lake infrastructure over the working MVP pipeline
**Deliverables:**
- MinIO Docker service with bucket initialization
- Nessie Docker service with REST API
- Iceberg table creation via PyIceberg
- DLT pipeline updated to write Iceberg tables
- dbt updated to read from Iceberg via DuckDB

**Files to Create:**
- docker/docker-compose.yml (MinIO + Nessie services)
- docker/minio/init-buckets.sh
- scripts/create_iceberg_tables.py
- dlt_pipeline/iceberg_destination.py
- docs/data_lake_architecture.md

**Success Criteria:** MinIO console accessible with created buckets; Nessie API responds; Iceberg tables created and queryable via DuckDB; full pipeline works with Iceberg backend
**Testing Criteria:** Data persisted in MinIO; Nessie catalog shows tables; schema evolution tested


### Sprint 10: Observability, Documentation, and Production Readiness (Days 33-36)

**Goals:** Add structured logging, health checks, comprehensive documentation, and CI configuration
**Deliverables:**
- Structured JSON logging across all components
- Health check endpoints and script
- Pipeline metrics tracking
- Complete documentation suite
- Makefile with all targets
- Linting configuration
- GitHub Actions workflow (template)

**Files to Create:**
- scripts/logging_config.py (enhanced), scripts/health_check.sh
- scripts/setup.sh
- docs/architecture.md, docs/data_lineage.md, docs/data_dictionary.md
- docs/setup_guide.md, docs/troubleshooting.md
- .github/workflows/ci.yml
- logs/.gitkeep

**Success Criteria:** All components emit structured JSON logs; health check script reports all services; documentation complete; `make lint` passes; `make test` passes all tests
**Testing Criteria:** Log format validated; health endpoints respond; docs render correctly

---

## Architecture Specification Summary

### Component Necessity Review

| Component | Necessary | Rationale |
|-----------|-----------|-----------|
| Mock_Data_Generator | Yes | No real data available; enables reproducible testing |
| DLT (dlt) | Yes | Demonstrates modern ingestion tooling; handles schema inference |
| DuckDB | Yes | Core query engine; lightweight, no server needed |
| dbt Core | Yes | Industry-standard transformation; demonstrates analytics engineering |
| MinIO | Yes (Phase 2) | Demonstrates object storage; Iceberg requires it |
| Apache Iceberg | Yes (Phase 2) | Demonstrates modern table format; schema evolution |
| Nessie | Yes (Phase 2) | Demonstrates catalog versioning; complements Iceberg |
| Cube.js | Yes (Phase 2) | Demonstrates semantic layer pattern; API exposure |
| Apache Superset | Yes | Visual deliverable; demonstrates dashboarding |
| Dagster | Yes (Phase 2) | Demonstrates orchestration; asset-based paradigm |
| IsolationForest | Yes | Demonstrates ML integration; anomaly detection |
| Docker Compose | Yes | Reproducible deployment; portfolio standard |

### Components NOT Included (and why)

| Component | Reason for Exclusion |
|-----------|---------------------|
| Apache Kafka/Spark | Overkill for batch processing of 10K-100K events |
| Airflow | Dagster is more modern and better for asset-based pipelines |
| Snowflake/BigQuery | Cloud dependency; MinIO+Iceberg demonstrates same concepts locally |
| Great Expectations | dbt tests sufficient for this scale; could add in future |
| MLflow | Joblib versioning sufficient; MLflow adds Docker complexity |
| Prometheus/Grafana | Documentation-only approach for observability; full stack too heavy |

---

## API Specification (Cube.js)

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /cubejs-api/v1/load | Query measures and dimensions |
| GET | /cubejs-api/v1/meta | Get available cubes, measures, dimensions |
| GET | /cubejs-api/v1/sql | Get generated SQL for a query |

### Example Queries

```json
// Total attacks
{"measures": ["KpiSummary.totalAttacks"]}

// Attack volume by day with date filter
{
  "measures": ["AttackVolumeByDay.attackCount"],
  "timeDimensions": [{"dimension": "AttackVolumeByDay.eventDate", "granularity": "day", "dateRange": "Last 30 days"}]
}

// Failed login rate by country
{
  "measures": ["SecurityEvents.failedLoginRate"],
  "dimensions": ["SecurityEvents.country"]
}
```

---

## Deployment Strategy

### Local Development
1. Clone repository
2. `make setup` (creates venv, installs dependencies, validates prerequisites)
3. `make generate-data` (produces mock data)
4. `make run-pipeline` (executes full pipeline: ingest → transform → detect)
5. `docker compose up` (starts all services)
6. Access Superset at localhost:8088, Dagit at localhost:3000, Cube.js at localhost:4000

### Docker Profiles
- `default`: All services (requires 16GB RAM)
- `lite`: MinIO + Nessie only (requires 4GB RAM)
- `dashboard`: Superset + Cube.js only (requires 8GB RAM)

---

*End of Requirements Specification*
