# Log Aggregation Approach

## Overview

The platform uses structured JSON logging across all Python components via the shared `scripts/logging_config.py` module.

## Log Format

Every log entry is a single JSON line with these fields:

```json
{
  "timestamp": "2024-01-15T14:32:07.123456+00:00",
  "level": "INFO",
  "component": "dlt_pipeline",
  "message": "Ingestion complete",
  "context": {
    "records_ingested": 10449,
    "elapsed_seconds": 18.5,
    "batch_id": "batch_20240115_001"
  }
}
```

## Components

| Component Name | Module | Purpose |
|---------------|--------|---------|
| `mock_data_generator` | mock_data.generator | Data generation metrics |
| `dlt_pipeline` | dlt_pipeline.pipeline | Ingestion metrics |
| `dlt_sources` | dlt_pipeline.sources | File processing |
| `dagster_assets` | dagster_pipeline.assets | Asset materialization |
| `ml_detection.features` | ml_detection.features | Feature extraction |
| `ml_detection.train` | ml_detection.train | Model training |
| `ml_detection.predict` | ml_detection.predict | Anomaly scoring |
| `ml_detection.evaluate` | ml_detection.evaluate | Model evaluation |
| `retry` | scripts.retry | Retry attempts |

## Pipeline Run Summaries

Each pipeline run writes a summary to `logs/pipeline_runs.jsonl` with:
- `run_id`, `start_time`, `end_time`, `duration_seconds`
- `stages_completed`, `stages_failed`
- `records_ingested`, `records_transformed`, `records_rejected`

## Duration Threshold Warnings

Stages exceeding 300 seconds emit a WARNING-level log:
```json
{"level": "WARNING", "message": "Stage exceeded duration threshold", "context": {"stage": "ingestion", "duration_seconds": 312, "threshold_seconds": 300}}
```

## Aggregation Strategy

For production deployments, logs can be aggregated via:
1. **File-based**: Collect `logs/*.jsonl` files with Filebeat/Fluentd
2. **stdout**: Container logs collected by Docker logging driver
3. **ELK Stack**: Ship JSON logs to Elasticsearch for search and visualization

The JSON format enables direct ingestion into any log management system without parsing.
