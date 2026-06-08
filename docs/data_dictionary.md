# Data Dictionary

## Bronze Layer

### security_bronze.security_events_resource

Raw ingested security events with DLT metadata.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| event_id | STRING | No | UUID v4 unique identifier |
| event_time | TIMESTAMP | No | When the event occurred (UTC) |
| username | STRING | No | User account |
| src_ip | STRING | No | Source IPv4 address |
| destination_ip | STRING | Yes | Destination IPv4 address |
| hostname | STRING | No | Machine hostname |
| event_type | STRING | No | One of 8 event categories |
| severity | STRING | No | low, medium, high, critical |
| status | STRING | No | success, failure, blocked, detected |
| country | STRING | No | ISO 3166-1 country code |
| operating_system | STRING | No | OS name |
| department | STRING | No | Organizational department |
| detection_time | TIMESTAMP | Yes | When attack was detected |
| resolution_time | TIMESTAMP | Yes | When incident was resolved |
| _ingested_at | STRING | No | UTC ingestion timestamp |
| _source_file | STRING | No | Source file path |
| _batch_id | STRING | No | Batch identifier (batch_YYYYMMDD_NNN) |

## Silver Layer

### security_silver.silver_events

Cleaned, deduplicated, and enriched security events.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| event_id | STRING | No | Deduplicated unique identifier |
| event_time | TIMESTAMP | No | Validated UTC timestamp |
| detection_time | TIMESTAMP | Yes | Detection time (attacks only) |
| resolution_time | TIMESTAMP | Yes | Resolution time (attacks only) |
| username | STRING | No | Lowercase username |
| src_ip | STRING | No | Validated IPv4 |
| destination_ip | STRING | Yes | Validated destination IPv4 |
| hostname | STRING | No | Uppercase hostname |
| event_type | STRING | No | Validated event category |
| severity | STRING | No | Lowercase severity |
| severity_rank | INTEGER | No | 1=low, 2=medium, 3=high, 4=critical |
| status | STRING | No | Event outcome |
| country | STRING | No | Country code |
| operating_system | STRING | No | OS name |
| department | STRING | No | Department name |
| hour_of_day | INTEGER | No | 0–23 |
| day_of_week | INTEGER | No | 1=Mon to 7=Sun |
| is_business_hours | BOOLEAN | No | True if 09:00–17:00 UTC |
| is_internal_ip | BOOLEAN | No | True if RFC1918 |
| is_attack_event | BOOLEAN | No | True if attack-related type |
| _ingested_at | STRING | No | Bronze ingestion timestamp |
| _source_file | STRING | No | Source file path |
| _batch_id | STRING | No | Batch identifier |

## Gold Layer

### security_silver.kpi_summary

Single-row table with computed security KPIs.

| Column | Type | Description |
|--------|------|-------------|
| total_attacks | INTEGER | Count of attack events |
| failed_login_rate | FLOAT | Failed logins / total logins (0.0–1.0) |
| avg_mttd_minutes | FLOAT | Mean Time To Detect in minutes |
| avg_mttr_minutes | FLOAT | Mean Time To Respond in minutes |
| sla_compliance | FLOAT | % incidents within 4-hour SLA (0.0–1.0) |
| computed_at | TIMESTAMP | When KPIs were computed |

### security_silver.attack_volume_by_day

Daily attack event counts.

| Column | Type | Description |
|--------|------|-------------|
| event_date | DATE | Date of attacks |
| attack_count | INTEGER | Attacks on this date |
| cumulative_attack_count | INTEGER | Running total |

### security_silver.attack_volume_by_country

Attack counts by source country.

| Column | Type | Description |
|--------|------|-------------|
| country | STRING | ISO country code |
| attack_count | INTEGER | Attacks from country |
| percentage_of_total | FLOAT | Proportion of all attacks |

### security_silver.hourly_event_summary

Hourly event aggregations (ML feature input).

| Column | Type | Description |
|--------|------|-------------|
| event_hour | TIMESTAMP | Hour window start |
| event_type | STRING | Event category |
| event_count | INTEGER | Events in window |
| unique_ips | INTEGER | Distinct source IPs |
| unique_users | INTEGER | Distinct usernames |

### security_gold.anomaly_results

IsolationForest anomaly detection results.

| Column | Type | Description |
|--------|------|-------------|
| window_start | TIMESTAMP | Hour window start |
| window_end | TIMESTAMP | Hour window end |
| anomaly_score | FLOAT | Score from -1 (anomalous) to 1 (normal) |
| is_anomaly | BOOLEAN | True if score < threshold (-0.5) |
| total_event_count | INTEGER | Events in window |
| top_contributing_feature | STRING | Most anomalous feature |
| model_version | STRING | Model version timestamp |
