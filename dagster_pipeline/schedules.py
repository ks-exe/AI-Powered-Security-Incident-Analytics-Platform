"""Cron-based schedule definitions for the Security Analytics pipeline.

Defines the daily pipeline schedule that runs at 02:00 UTC.

Requirements: 8.5
"""

from dagster import ScheduleDefinition

from dagster_pipeline.jobs import security_analytics_pipeline

# Daily schedule - runs the full pipeline at 02:00 UTC
daily_pipeline_schedule = ScheduleDefinition(
    job=security_analytics_pipeline,
    cron_schedule="0 2 * * *",
    execution_timezone="UTC",
    description="Run the full security analytics pipeline daily at 02:00 UTC",
)
