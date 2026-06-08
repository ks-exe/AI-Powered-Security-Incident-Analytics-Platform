"""File-based sensors for the Security Analytics pipeline.

Detects new mock data files and triggers pipeline runs automatically.

Requirements: 8.6
"""

from pathlib import Path

from dagster import (
    RunRequest,
    SensorEvaluationContext,
    sensor,
)

from dagster_pipeline.jobs import security_analytics_pipeline


@sensor(
    job=security_analytics_pipeline,
    minimum_interval_seconds=60,
    description="Detects new .jsonl files in mock_data/ directory and triggers pipeline runs",
)
def new_data_file_sensor(context: SensorEvaluationContext):
    """Sensor that watches for new JSONL files in the mock_data directory.

    Tracks the last seen modification time via cursor to avoid re-triggering
    on already-processed files.
    """
    data_dir = Path("mock_data")
    if not data_dir.exists():
        return

    # Get the last processed timestamp from cursor
    last_mtime = float(context.cursor) if context.cursor else 0.0

    # Find all JSONL files
    jsonl_files = sorted(data_dir.glob("*.jsonl"))
    if not jsonl_files:
        return

    # Check for new or modified files
    max_mtime = last_mtime
    new_files = []

    for filepath in jsonl_files:
        file_mtime = filepath.stat().st_mtime
        if file_mtime > last_mtime:
            new_files.append(filepath.name)
            max_mtime = max(max_mtime, file_mtime)

    if new_files:
        context.update_cursor(str(max_mtime))
        yield RunRequest(
            run_key=f"new_data_{max_mtime}",
            run_config={},
            tags={
                "trigger": "file_sensor",
                "new_files": ",".join(new_files),
            },
        )
