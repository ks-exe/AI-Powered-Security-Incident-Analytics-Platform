"""Dagster orchestration for the Security Incident Analytics Platform.

Defines software-defined assets, jobs, schedules, sensors, and resources for
the complete data pipeline. Supports:
- Automated daily scheduling (02:00 UTC)
- File-based sensor for new data detection
- Manual asset materialization via Dagit UI
- Structured logging on pipeline completion
- Asset lineage tracking in Dagit asset graph

Requirements: 8.7, 8.8, 8.9, 8.10
"""

from dagster import Definitions

from dagster_pipeline.assets import (
    anomaly_results,
    bronze_events,
    gold_attack_by_country,
    gold_attack_by_day,
    gold_hourly_summary,
    gold_kpi_summary,
    raw_security_events,
    silver_events,
)
from dagster_pipeline.jobs import security_analytics_pipeline
from dagster_pipeline.resources import dbt_resource, duckdb_resource
from dagster_pipeline.schedules import daily_pipeline_schedule
from dagster_pipeline.sensors import new_data_file_sensor

defs = Definitions(
    assets=[
        raw_security_events,
        bronze_events,
        silver_events,
        gold_kpi_summary,
        gold_attack_by_day,
        gold_attack_by_country,
        gold_hourly_summary,
        anomaly_results,
    ],
    jobs=[security_analytics_pipeline],
    schedules=[daily_pipeline_schedule],
    sensors=[new_data_file_sensor],
    resources={
        "duckdb": duckdb_resource,
        "dbt": dbt_resource,
    },
)
