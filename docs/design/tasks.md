# Implementation Plan: AI-Powered Security Incident Analytics Platform

## Overview

This implementation plan converts the technical design into actionable coding tasks organized by the 10-sprint roadmap. Each task builds incrementally on previous work, ensuring no orphaned code. The platform is implemented in Python (data pipeline, ML), SQL (dbt transformations), and JavaScript (Cube.js schemas). Property-based tests use Hypothesis.

## Tasks

- [x] 1. Project Foundation and Mock Data Generator (Sprint 1)
  - [x] 1.1 Initialize project structure and configuration files
    - Create `pyproject.toml` with pinned dependencies (faker, numpy, pydantic, dlt, dbt-duckdb, scikit-learn, pandas, dagster, hypothesis, pytest, ruff)
    - Create `Makefile` with targets: setup, generate-data, ingest, transform, detect-anomalies, run-pipeline, test, test-unit, test-property, test-integration, lint, docs, docker-up, docker-down, clean
    - Create `.gitignore` excluding mock_data/*.parquet, mock_data/*.jsonl, *.duckdb, .env, __pycache__/, venv/, docker volumes
    - Create `.env.example` with placeholder credentials for MinIO, Superset, Cube.js
    - Create directory structure with `__init__.py` files for: mock_data/, dlt_pipeline/, ml_detection/, dagster/, scripts/, tests/unit/, tests/integration/
    - Create `data/.gitkeep`, `models/.gitkeep`, `logs/.gitkeep`
    - _Requirements: 12.1, 12.2, 12.3, 12.6, 12.9_

  - [x] 1.2 Implement shared logging utility
    - Create `scripts/__init__.py` and `scripts/logging_config.py` with JSONFormatter class
    - Implement `get_logger(component: str)` returning configured logger with JSON output
    - Implement structured log fields: timestamp (ISO8601), level, component, message, context
    - _Requirements: 10.1, 10.2_

  - [x] 1.3 Implement retry utility
    - Create `scripts/retry.py` with `with_retry` decorator
    - Implement exponential backoff: 1s, 2s, 4s (backoff_base * 2^attempt)
    - Support configurable max_retries and retryable_exceptions tuple
    - _Requirements: 10.9_

  - [x] 1.4 Implement SecurityEvent Pydantic schema
    - Create `mock_data/schemas.py` with EventType enum (8 values), Severity enum (4 values)
    - Implement SecurityEvent BaseModel with all fields per design specification
    - Add field validators for event_id (UUID), src_ip (IPv4), event_time (UTC timestamp)
    - _Requirements: 1.2, 1.3_

  - [x] 1.5 Implement statistical distributions module
    - Create `mock_data/distributions.py` with severity weight distribution (low=40%, medium=30%, high=20%, critical=10%)
    - Implement event_type weight distribution with configurable probabilities
    - Implement temporal distribution with business-hour clustering (70% during 09:00-17:00 UTC)
    - Implement IP address generation: 60% internal (RFC1918), 40% external
    - _Requirements: 1.4, 1.5, 1.6_

  - [x] 1.6 Implement anomaly injection module
    - Create `mock_data/anomaly_injector.py` with AnomalyConfig dataclass
    - Implement burst injection: 50+ failed_logins from single IP within 5 minutes (3-5 burst windows)
    - Implement off-hours escalation: privilege_escalation events outside business hours
    - Implement geographic anomalies: events from unusual countries (KP, IR, SY)
    - _Requirements: 1.9, 1.10_

  - [x] 1.7 Implement main generator orchestrator
    - Create `mock_data/generator.py` with GeneratorConfig dataclass
    - Implement `generate_security_events(config)` producing list of event dicts
    - Support deterministic output via seed parameter (numpy random state)
    - Generate detection_time and resolution_time for attack events per schema spec
    - Implement `write_events(events, config)` outputting JSONL and Parquet to mock_data/
    - Create `mock_data/config.yaml` with default configuration values
    - _Requirements: 1.1, 1.7, 1.8_

  - [x]* 1.8 Write property tests for Mock Data Generator (Properties 1-4)
    - **Property 1: Generated events conform to schema** — validate all required fields, enum values, UUID format, IPv4 format, non-null detection_time/resolution_time for attack events
    - **Property 2: Generator produces exact requested count** — for any N in [10000, 1000000], output length equals N
    - **Property 3: Generator determinism with seed** — same seed + config produces identical output
    - **Property 4: Serialization round-trip preserves data** — JSONL write/read and Parquet write/read produce equivalent records
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.5, 1.6, 1.7, 1.8**

  - [x]* 1.9 Write unit tests for Mock Data Generator
    - Test schema validation with known inputs
    - Test severity distribution matches configured weights (within statistical tolerance)
    - Test business-hour clustering ratio
    - Test anomaly injection produces expected burst patterns
    - Test field correlations (internal IPs ↔ departments, attacks ↔ higher severity)
    - _Requirements: 1.4, 1.5, 1.9, 1.10_

  - [x] 1.10 Create initial README.md
    - Write project overview with architecture description
    - Include Mermaid architecture diagram
    - Document technology stack with version numbers
    - Write prerequisites section and quick-start guide (under 5 commands)
    - Document project structure
    - _Requirements: 12.1_

- [x] 2. Checkpoint — Sprint 1 validation
  - Ensure `make generate-data` produces valid 10K-event dataset in JSONL and Parquet
  - Ensure `make test-unit` passes all unit tests for mock data generator
  - Ensure all property tests (1-4) pass with Hypothesis (100+ iterations)
  - Ask the user if questions arise.

- [x] 3. DLT Ingestion Pipeline + Bronze Layer (Sprint 2)
  - [x] 3.1 Implement record validator
    - Create `dlt_pipeline/validators.py` with `validate_record(record)` function
    - Return `(is_valid, list_of_error_messages)` tuple
    - Validate required fields: event_id, event_time, event_type present and non-empty
    - Validate event_type is one of 8 accepted values
    - _Requirements: 3.4_

  - [x] 3.2 Implement DLT source and resource definitions
    - Create `dlt_pipeline/sources.py` with `@dlt.source` security_logs_source
    - Implement `@dlt.resource` security_events_resource with write_disposition="merge", primary_key="event_id"
    - Add metadata enrichment: _ingested_at (UTC), _source_file (path), _batch_id (batch_YYYYMMDD_NNN format)
    - Implement dead letter routing for invalid records via validator
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 3.3 Implement DLT pipeline execution
    - Create `dlt_pipeline/pipeline.py` with IngestionResult dataclass
    - Implement `run_ingestion()` function with DuckDB destination
    - Support incremental loading via dlt state management
    - Ensure idempotency: re-running with same data produces no duplicates
    - Log completion metrics: records_ingested, records_rejected, elapsed_seconds, records_per_second
    - Create `dlt_pipeline/config.yaml` with pipeline configuration
    - _Requirements: 3.5, 3.6, 3.7, 3.8_

  - [x]* 3.4 Write property tests for DLT Pipeline (Properties 5-7)
    - **Property 5: Ingestion preserves source fields and adds metadata** — all original fields unchanged, _ingested_at/_source_file/_batch_id non-null and correctly formatted
    - **Property 6: Invalid records route to dead letter table** — records missing required fields go to dead_letter_events, valid records go to raw_security_events
    - **Property 7: Pipeline idempotency** — running N times with same input produces same record count as running once
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.7**

  - [x]* 3.5 Write integration tests for DLT Pipeline
    - Test end-to-end ingestion of sample JSONL file into DuckDB
    - Verify record count matches source file
    - Verify metadata columns populated correctly
    - Verify dead letter table captures malformed records
    - Verify idempotent re-run does not duplicate records
    - _Requirements: 3.1, 3.5, 3.7_

- [x] 4. Checkpoint — Sprint 2 validation
  - Ensure `make ingest` loads all mock data into DuckDB Bronze layer
  - Ensure dead letter table captures malformed records
  - Ensure re-running ingestion does not duplicate data
  - Ask the user if questions arise.

- [x] 5. dbt Silver Layer Transformations (Sprint 3)
  - [x] 5.1 Initialize dbt project structure
    - Create `dbt_project/dbt_project.yml` with project name and configuration
    - Create `dbt_project/profiles.yml` configured for DuckDB local development
    - Create `dbt_project/packages.yml` with dbt-utils dependency
    - Create source definition for Bronze layer tables in `dbt_project/models/staging/_staging_models.yml`
    - _Requirements: 4.7, 4.10_

  - [x] 5.2 Implement dbt macros for reusable logic
    - Create `dbt_project/macros/validate_ipv4.sql` — validates IPv4 format using regex
    - Create `dbt_project/macros/severity_rank.sql` — maps severity string to integer (low=1, medium=2, high=3, critical=4)
    - Create `dbt_project/macros/is_rfc1918.sql` — checks if IP is in RFC1918 ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - _Requirements: 4.3, 4.4_

  - [x] 5.3 Implement staging model
    - Create `dbt_project/models/staging/stg_security_events.sql` selecting from Bronze source
    - Apply basic type casting and column selection
    - _Requirements: 4.1_

  - [x] 5.4 Implement Silver layer model with deduplication and enrichment
    - Create `dbt_project/models/silver/silver_events.sql` as incremental model (unique_key: event_id)
    - Implement deduplication: ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY _ingested_at DESC)
    - Implement validation: reject unparseable timestamps, invalid IPs, unknown severities
    - Add derived fields: hour_of_day, day_of_week, is_business_hours, is_internal_ip, severity_rank, is_attack_event
    - Standardize: username to lowercase, hostname to uppercase, severity to lowercase
    - Create `dbt_project/models/silver/_silver_models.yml` with column descriptions and tests
    - _Requirements: 4.2, 4.3, 4.4_

  - [x] 5.5 Add dbt data quality tests for Silver layer
    - Add uniqueness test on event_id
    - Add not_null tests on all non-nullable fields
    - Add accepted_values test for event_type (8 types) and severity (4 levels)
    - Add custom test for severity_rank range (1-4)
    - Create `dbt_project/seeds/event_type_mapping.csv` for reference data
    - _Requirements: 4.6_

  - [x]* 5.6 Write property tests for Silver layer (Properties 8-9)
    - **Property 8: Silver layer deduplication produces unique event_ids** — after transformation, exactly one record per event_id with latest _ingested_at
    - **Property 9: Derived field computation correctness** — hour_of_day, day_of_week, is_business_hours, is_internal_ip, severity_rank, is_attack_event all correctly computed
    - **Validates: Requirements 4.2, 4.4**

  - [x]* 5.7 Write integration tests for dbt Silver models
    - Test `dbt build` completes successfully on test dataset
    - Verify deduplication removes duplicate event_ids
    - Verify derived fields computed correctly for known inputs
    - Verify all dbt tests pass
    - _Requirements: 4.2, 4.3, 4.4, 4.6_

- [x] 6. Checkpoint — Sprint 3 validation
  - Ensure `make transform` runs dbt build successfully
  - Ensure Silver table has all enriched columns
  - Ensure all dbt tests pass
  - Ask the user if questions arise.

- [x] 7. dbt Gold Layer + Security KPIs (Sprint 4)
  - [x] 7.1 Implement KPI summary Gold model
    - Create `dbt_project/models/gold/kpi_summary.sql` as materialized table
    - Compute total_attacks: COUNT(*) WHERE is_attack_event = true
    - Compute failed_login_rate: COUNT(failed_login) / COUNT(failed_login + successful_login)
    - Compute avg_mttd_minutes: AVG(detection_time - event_time) in minutes WHERE detection_time IS NOT NULL
    - Compute avg_mttr_minutes: AVG(resolution_time - detection_time) in minutes WHERE resolution_time IS NOT NULL
    - Compute sla_compliance: COUNT(MTTR ≤ 240 min) / COUNT(resolution_time IS NOT NULL)
    - Add computed_at timestamp
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.8_

  - [x] 7.2 Implement attack volume by day Gold model
    - Create `dbt_project/models/gold/attack_volume_by_day.sql` as materialized table
    - Compute attack_count per DATE(event_time) WHERE is_attack_event = true
    - Compute cumulative_attack_count using window function
    - _Requirements: 5.6_

  - [x] 7.3 Implement attack volume by country Gold model
    - Create `dbt_project/models/gold/attack_volume_by_country.sql` as materialized table
    - Compute attack_count per country WHERE is_attack_event = true
    - Compute percentage_of_total as attack_count / SUM(attack_count)
    - _Requirements: 5.7_

  - [x] 7.4 Implement hourly event summary Gold model
    - Create `dbt_project/models/gold/hourly_event_summary.sql` as materialized table
    - Compute per hourly window: event_count, unique_ips (COUNT DISTINCT src_ip), unique_users (COUNT DISTINCT username)
    - Include event_type grouping for ML feature engineering input
    - _Requirements: 5.9_

  - [x] 7.5 Add Gold layer schema and tests
    - Create `dbt_project/models/gold/_gold_models.yml` with column descriptions
    - Add custom test `assert_kpi_ranges.sql` validating rates between 0.0 and 1.0
    - Add relationship tests between Gold and Silver tables
    - Generate dbt documentation via `dbt docs generate`
    - _Requirements: 4.6, 4.8_

  - [x]* 7.6 Write property tests for Gold layer KPIs (Properties 10-11)
    - **Property 10: KPI computation correctness** — total_attacks, failed_login_rate, avg_mttd, avg_mttr, sla_compliance all match formula definitions
    - **Property 11: Aggregation grouping correctness** — attack_volume_by_day has one row per date, attack_volume_by_country has one row per country, hourly_event_summary has correct counts
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.9**

  - [x]* 7.7 Write unit tests for KPI calculations
    - Test each KPI formula with known-input/known-output datasets
    - Test edge cases: no attack events, all events are attacks, no login events
    - Test SLA compliance with boundary values (exactly 240 minutes)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 8. Checkpoint — Sprint 4 validation
  - Ensure all Gold models materialize successfully
  - Ensure KPI values are within expected ranges for mock data
  - Ensure `dbt docs generate` shows complete DAG
  - Ask the user if questions arise.

- [x] 9. Apache Superset Dashboard (Sprint 5)
  - [x] 9.1 Create Docker Compose configuration for Superset
    - Add Superset service to `docker-compose.yml` on port 8088
    - Create `docker/superset/Dockerfile` with custom Superset image
    - Create `docker/superset/superset_config.py` with database and security settings
    - Configure health check: `curl -f http://localhost:8088/health`
    - Set restart policy: unless-stopped
    - _Requirements: 7.8, 2.1_

  - [x] 9.2 Implement Superset initialization script
    - Create `docker/superset/init_superset.sh` to bootstrap admin user
    - Configure database connection to DuckDB (MVP) or Cube.js (Production)
    - Set up RBAC with admin role
    - _Requirements: 7.7, 7.8_

  - [x] 9.3 Create Security Overview dashboard definition
    - Create dashboard with 5 KPI cards: total_attacks, failed_login_rate, avg_mttd, avg_mttr, sla_compliance
    - Add time-series line chart for attack_volume_by_day
    - Add horizontal bar chart for attack_volume_by_country (top 10)
    - Add bar chart for event count by event_type (all 8 types)
    - Add donut chart for severity distribution with percentage labels
    - Add anomaly timeline chart with anomaly_score and threshold line at -0.5
    - Add global filters: date range, event_type, severity, country
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.9_

  - [x] 9.4 Export dashboard configuration for version control
    - Export dashboard as JSON to `dashboards/security_overview.json`
    - Document dashboard import/export process
    - _Requirements: 7.10_

- [x] 10. Checkpoint — Sprint 5 validation
  - Ensure `docker compose up superset` starts Superset successfully
  - Ensure dashboard displays all KPI visualizations with data
  - Ensure filters update all charts within 3 seconds
  - Ask the user if questions arise.

- [x] 11. Cube.js Semantic Layer (Sprint 6)
  - [x] 11.1 Create Cube.js Docker service configuration
    - Add Cube.js service to `docker-compose.yml` on port 4000
    - Create `cube/.env` with DuckDB connection string and CUBEJS_API_SECRET
    - Create `cube/cube.js` configuration file with DuckDB driver
    - Configure health check: `curl -f http://localhost:4000/readyz`
    - Configure CORS for Superset integration
    - _Requirements: 6.7, 6.9_

  - [x] 11.2 Implement Cube.js schema definitions
    - Create `cube/schema/KpiSummary.js` with measures: totalAttacks, failedLoginRate, avgMttdMinutes, avgMttrMinutes, slaCompliance
    - Create `cube/schema/AttackVolumeByDay.js` with attackCount, cumulativeAttackCount measures and eventDate time dimension
    - Create `cube/schema/AttackVolumeByCountry.js` with attackCount measure and country dimension
    - Create `cube/schema/HourlyEventSummary.js` with eventCount, uniqueIps, uniqueUsers measures
    - Create `cube/schema/SecurityEvents.js` with full event dimensions and measures
    - Create `cube/schema/AnomalyResults.js` with anomalyScore measure and isAnomaly dimension
    - _Requirements: 6.4_

  - [x] 11.3 Configure pre-aggregations and filtering
    - Add daily pre-aggregation to AttackVolumeByDay cube
    - Add hourly pre-aggregation to HourlyEventSummary cube
    - Configure time-dimension filtering on event_time (date range, hour, day of week, month)
    - Configure dimension filtering on event_type, severity, country, department, is_anomaly
    - _Requirements: 6.5, 6.6, 6.10_

  - [x] 11.4 Update Superset to connect via Cube.js
    - Update Superset database connection to use Cube.js REST API
    - Verify all dashboard charts render through semantic layer
    - Document API endpoints: /cubejs-api/v1/load, /cubejs-api/v1/meta, /cubejs-api/graphql
    - Create `docs/api_specification.md` with example queries
    - _Requirements: 6.1, 6.2, 6.3, 6.8_

- [x] 12. Checkpoint — Sprint 6 validation
  - Ensure Cube.js playground accessible on port 4000
  - Ensure REST API returns KPI data with response time < 5 seconds
  - Ensure GraphQL queries work for all cubes
  - Ask the user if questions arise.

- [ ] 13. Dagster Orchestration (Sprint 7)
  - [x] 13.1 Initialize Dagster project structure
    - Create `dagster/workspace.yaml` with repository configuration
    - Create `dagster/__init__.py` with Definitions object
    - Create `dagster/resources.py` with DuckDB resource and dbt resource (dagster-dbt)
    - _Requirements: 8.7_

  - [-] 13.2 Implement software-defined assets
    - Create `dagster/assets.py` with @asset definitions for:
      - `raw_security_events` (group: ingestion) — calls Mock Data Generator
      - `bronze_events` (group: ingestion) — calls DLT Pipeline
      - `silver_events` (group: transformation) — runs dbt Silver models
      - `gold_kpi_summary` (group: analytics) — runs dbt Gold KPI model
      - `gold_attack_by_day` (group: analytics) — runs dbt Gold attack by day model
      - `gold_attack_by_country` (group: analytics) — runs dbt Gold attack by country model
      - `gold_hourly_summary` (group: analytics) — runs dbt Gold hourly summary model
      - `anomaly_results` (group: ml) — runs anomaly detection pipeline
    - Define asset dependencies via AssetIn
    - Add metadata and descriptions to each asset
    - _Requirements: 8.2, 8.3, 8.8_

  - [ ] 13.3 Implement pipeline job and schedule
    - Create `dagster/jobs.py` with `security_analytics_pipeline` job selecting all assets
    - Create `dagster/schedules.py` with daily schedule (cron: `0 2 * * *` UTC)
    - Create `dagster/sensors.py` with file-based sensor detecting new mock data files
    - Implement failure handling: mark run as failed, log error with stage name and stack trace, halt downstream
    - _Requirements: 8.1, 8.5, 8.6, 8.9_

  - [ ] 13.4 Create Dagster Docker configuration
    - Create `dagster/Dockerfile` for dagster-webserver and dagster-daemon
    - Add dagster-webserver service to `docker-compose.yml` on port 3000
    - Add dagster-daemon service to `docker-compose.yml`
    - Configure health check: `curl -f http://localhost:3000/server_info`
    - _Requirements: 8.4, 8.7_

  - [ ] 13.5 Implement pipeline run logging
    - Emit structured log entry on successful completion: run_id, duration_seconds, assets_materialized, records_processed
    - Track asset lineage in Dagit asset graph
    - Support manual asset materialization for individual assets
    - _Requirements: 8.10, 8.8, 8.9_

- [ ] 14. Checkpoint — Sprint 7 validation
  - Ensure Dagit UI accessible on port 3000
  - Ensure full pipeline job executes successfully end-to-end
  - Ensure asset graph shows correct dependencies
  - Ask the user if questions arise.

- [ ] 15. AI Anomaly Detection (Sprint 8)
  - [ ] 15.1 Implement feature engineering module
    - Create `ml_detection/features.py` with FEATURE_COLUMNS list (10 features)
    - Implement `extract_features(db_path)` querying hourly_event_summary from DuckDB
    - Compute all 10 feature columns per hourly window: total_event_count, unique_src_ips, unique_users, failed_login_count, failed_login_ratio, attack_event_count, avg_severity_rank, critical_event_count, unique_countries, events_outside_business_hours_ratio
    - Implement `validate_features(features_df)` checking expected columns and no NaN values
    - _Requirements: 9.2_

  - [ ] 15.2 Implement model training module
    - Create `ml_detection/train.py` with TrainingConfig and TrainingResult dataclasses
    - Implement `train_model(features_df, config)` using IsolationForest (n_estimators=100, contamination=0.05, random_state=42)
    - Save model artifact as joblib with versioned filename: `models/isolation_forest_v{YYYYMMDD_HHMMSS}.joblib`
    - Validate anomaly_percentage between 1% and 15% (log WARNING if outside range)
    - Log training metrics: contamination_parameter, n_estimators, n_samples_trained, n_anomalies_detected, anomaly_percentage, training_duration_seconds
    - _Requirements: 9.6, 9.7, 9.8, 9.10_

  - [ ] 15.3 Implement model prediction module
    - Create `ml_detection/predict.py` with PredictionResult dataclass
    - Implement `predict_anomalies(features_df, model_path, threshold=-0.5)` scoring all windows
    - Assign anomaly_score (-1 to 1) and is_anomaly flag based on threshold
    - Compute top_contributing_feature via permutation importance for anomalous windows
    - Implement `persist_results(results, db_path, model_version)` writing to anomaly_results Gold table
    - _Requirements: 9.3, 9.4, 9.5, 9.9_

  - [ ] 15.4 Implement model evaluation module
    - Create `ml_detection/evaluate.py` with evaluation metrics
    - Compute precision: percentage of flagged windows containing injected anomaly patterns
    - Compute recall: percentage of injected anomaly windows that are flagged
    - Log both metrics; target precision > 0.7 and recall > 0.6
    - Create `ml_detection/config.yaml` with ML configuration defaults
    - _Requirements: 9.10_

  - [ ]* 15.5 Write property tests for Anomaly Detection (Properties 12-14)
    - **Property 12: Feature extraction correctness** — all 10 features correctly computed for any hourly window of events
    - **Property 13: Anomaly threshold classification** — anomaly_score in [-1, 1], is_anomaly true iff anomaly_score < threshold
    - **Property 14: Anomaly result persistence round-trip** — persist and read back produces matching records with all required columns
    - **Validates: Requirements 9.2, 9.3, 9.4, 9.5, 9.9**

  - [ ]* 15.6 Write unit and integration tests for Anomaly Detection
    - Unit test feature vector computation with known data
    - Unit test threshold classification logic
    - Integration test full train → predict → persist cycle
    - Verify model artifact saved with correct naming convention
    - Verify anomaly percentage within expected range
    - _Requirements: 9.1, 9.2, 9.3, 9.5_

- [ ] 16. Checkpoint — Sprint 8 validation
  - Ensure `make detect-anomalies` trains model and produces anomaly results
  - Ensure injected anomalies detected with precision > 0.7
  - Ensure model artifact saved with version timestamp
  - Ask the user if questions arise.

- [ ] 17. Data Lake Integration — MinIO + Iceberg + Nessie (Sprint 9)
  - [ ] 17.1 Create MinIO Docker service with bucket initialization
    - Add MinIO service to `docker-compose.yml` on ports 9000 (API) and 9001 (console)
    - Create `docker/minio/init-buckets.sh` creating buckets: bronze-layer, silver-layer, gold-layer, raw-data
    - Add minio-init container using minio/mc to run bucket creation
    - Configure credentials via MINIO_ROOT_USER and MINIO_ROOT_PASSWORD environment variables
    - Add health check: `curl -f http://localhost:9000/minio/health/live`
    - _Requirements: 2.3, 2.5_

  - [ ] 17.2 Create Nessie Docker service
    - Add Nessie service to `docker-compose.yml` on port 19120
    - Configure in-memory store for development (RocksDB for production profile)
    - Add health check: `curl -f http://localhost:19120/api/v2/config`
    - _Requirements: 2.4_

  - [ ] 17.3 Implement Iceberg table creation and registration
    - Create `scripts/create_iceberg_tables.py` using PyIceberg
    - Register all tables in Nessie catalog with namespace matching medallion layers
    - Support schema evolution on Iceberg tables without data rewrite
    - _Requirements: 2.6, 2.7_

  - [ ] 17.4 Create Docker Compose lite profile
    - Create `docker-compose.lite.yml` with only MinIO and Nessie services
    - Ensure lite profile uses under 4GB RAM
    - Document profile usage in README
    - _Requirements: 2.2_

  - [ ] 17.5 Update DLT pipeline for Iceberg destination
    - Create `dlt_pipeline/iceberg_destination.py` with Iceberg write support
    - Update pipeline to write to MinIO/Iceberg when production profile is active
    - Maintain DuckDB destination for MVP profile
    - _Requirements: 3.1_

  - [ ] 17.6 Create setup and validation script
    - Create `scripts/setup.sh` validating prerequisites: Docker, Docker Compose, minimum RAM (16GB), disk space (20GB)
    - Add error handling: descriptive error messages on service failure, non-zero exit code
    - Document minimum system requirements in README
    - _Requirements: 2.8, 2.9, 2.10_

  - [ ] 17.7 Create data lake architecture documentation
    - Create `docs/data_lake_architecture.md` documenting MinIO + Iceberg + Nessie integration
    - Document schema evolution workflow
    - Document Nessie branching and versioning capabilities
    - _Requirements: 2.7_

- [ ] 18. Checkpoint — Sprint 9 validation
  - Ensure MinIO console accessible with created buckets
  - Ensure Nessie API responds on port 19120
  - Ensure Iceberg tables created and queryable via DuckDB
  - Ensure full pipeline works with Iceberg backend
  - Ask the user if questions arise.

- [ ] 19. Observability, Documentation, and Production Readiness (Sprint 10)
  - [ ] 19.1 Enhance structured logging across all components
    - Update all Python components to use shared `get_logger(component)` utility
    - Ensure all log entries include: timestamp, level, component, message, context (run_id, batch_id)
    - Implement duration threshold warnings (default: 300 seconds per stage)
    - Write pipeline run summaries to `logs/pipeline_runs.jsonl`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.8_

  - [ ]* 19.2 Write property test for structured logging (Property 15)
    - **Property 15: Structured log format validity** — all log output is valid JSON with required fields: timestamp (ISO8601), level (DEBUG/INFO/WARNING/ERROR), component (non-empty string), message (string)
    - **Validates: Requirements 10.1**

  - [ ] 19.3 Implement health check endpoints and script
    - Add HTTP health check endpoints to each containerized service returning JSON: `{"status": "healthy"|"unhealthy", "service": "<name>", "uptime_seconds": <int>}`
    - Create `scripts/health_check.sh` querying all service endpoints and reporting overall status
    - Implement consecutive failure counting and logging
    - Add freshness check mode (`--check-freshness`) for SLA monitoring
    - _Requirements: 10.5, 10.6, 10.7_

  - [ ] 19.4 Implement pipeline metrics tracking
    - Track per-run metrics: total_duration_seconds, records_ingested, records_transformed, records_rejected, stages_completed, stages_failed
    - Store metrics in DuckDB pipeline_metrics table
    - Emit WARNING when stage exceeds duration threshold
    - _Requirements: 10.3, 10.4_

  - [ ] 19.5 Create comprehensive documentation suite
    - Create `docs/architecture.md` with system architecture, component interactions, deployment diagrams
    - Create `docs/data_lineage.md` showing complete data flow from Mock Generator through all layers
    - Create `docs/data_dictionary.md` documenting every table, column, data type, and business meaning
    - Create `docs/setup_guide.md` with detailed installation and configuration instructions
    - Create `docs/troubleshooting.md` with common issues and solutions
    - _Requirements: 11.1, 11.4, 11.5, 12.8_

  - [ ] 19.6 Configure linting and CI workflow
    - Configure ruff in `pyproject.toml` with [tool.ruff] section
    - Create `.github/workflows/ci.yml` with stages: lint → unit tests → property tests → dbt build → integration tests → Docker validation
    - Configure pytest markers: unit, integration, property, smoke
    - Ensure `make lint` passes with ruff
    - _Requirements: 12.10_

  - [ ] 19.7 Finalize Makefile and configuration management
    - Ensure all Makefile targets work: setup, generate-data, ingest, transform, detect-anomalies, run-pipeline, test, test-unit, test-property, test-integration, test-dbt, test-smoke, lint, docs, docker-up, docker-down, clean
    - Verify `.env.example` documents all environment variables
    - Verify all config.yaml files have sensible defaults
    - Update README.md with final project structure and all documentation links
    - _Requirements: 12.7, 12.9_

  - [ ] 19.8 Document log aggregation approach
    - Document Docker Compose logging drivers configuration
    - Provide instructions for connecting to ELK or Loki (documentation only)
    - _Requirements: 10.10_

- [ ] 20. Final Checkpoint — Full platform validation
  - Ensure all components emit structured JSON logs
  - Ensure health check script reports all services healthy
  - Ensure documentation is complete and renders correctly
  - Ensure `make lint` passes
  - Ensure `make test` passes all unit, property, and integration tests
  - Ensure `make run-pipeline` executes full end-to-end pipeline successfully
  - Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability (format: Requirement#.Criterion#)
- Checkpoints ensure incremental validation at each sprint boundary
- Property tests validate universal correctness properties defined in the design document using Hypothesis (100+ iterations each)
- Unit tests validate specific examples and edge cases
- The implementation follows the sprint roadmap: Sprints 1-4 (MVP core), Sprints 5-7 (serving + orchestration), Sprints 8-10 (ML + production infrastructure)
- Python is the primary implementation language; SQL for dbt models; JavaScript for Cube.js schemas
- All Docker services use health checks and restart policies for reliability
- Configuration is externalized to .env files and config.yaml — no hardcoded magic numbers

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4", "1.10"] },
    { "id": 2, "tasks": ["1.5", "1.6"] },
    { "id": 3, "tasks": ["1.7"] },
    { "id": 4, "tasks": ["1.8", "1.9"] },
    { "id": 5, "tasks": ["3.1"] },
    { "id": 6, "tasks": ["3.2"] },
    { "id": 7, "tasks": ["3.3"] },
    { "id": 8, "tasks": ["3.4", "3.5"] },
    { "id": 9, "tasks": ["5.1"] },
    { "id": 10, "tasks": ["5.2"] },
    { "id": 11, "tasks": ["5.3"] },
    { "id": 12, "tasks": ["5.4"] },
    { "id": 13, "tasks": ["5.5", "5.6", "5.7"] },
    { "id": 14, "tasks": ["7.1", "7.2", "7.3", "7.4"] },
    { "id": 15, "tasks": ["7.5", "7.6", "7.7"] },
    { "id": 16, "tasks": ["9.1", "11.1"] },
    { "id": 17, "tasks": ["9.2", "11.2"] },
    { "id": 18, "tasks": ["9.3", "11.3"] },
    { "id": 19, "tasks": ["9.4", "11.4"] },
    { "id": 20, "tasks": ["13.1"] },
    { "id": 21, "tasks": ["13.2"] },
    { "id": 22, "tasks": ["13.3", "13.4"] },
    { "id": 23, "tasks": ["13.5"] },
    { "id": 24, "tasks": ["15.1"] },
    { "id": 25, "tasks": ["15.2"] },
    { "id": 26, "tasks": ["15.3"] },
    { "id": 27, "tasks": ["15.4", "15.5", "15.6"] },
    { "id": 28, "tasks": ["17.1", "17.2"] },
    { "id": 29, "tasks": ["17.3", "17.4"] },
    { "id": 30, "tasks": ["17.5", "17.6", "17.7"] },
    { "id": 31, "tasks": ["19.1", "19.3", "19.5"] },
    { "id": 32, "tasks": ["19.2", "19.4", "19.6", "19.8"] },
    { "id": 33, "tasks": ["19.7"] }
  ]
}
```
