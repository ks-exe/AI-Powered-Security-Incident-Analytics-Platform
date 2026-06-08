"""DLT source and resource definitions for security log ingestion.

Defines the dlt source and resources for reading JSONL files from a data directory,
validating records, enriching with metadata, and routing invalid records to a
dead letter table.

Requirements: 3.1, 3.2, 3.3, 3.4
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import dlt

from dlt_pipeline.validators import validate_record
from scripts.logging_config import get_logger

logger = get_logger("dlt_sources")


def _generate_batch_id(sequence_number: int) -> str:
    """Generate a batch ID in format batch_YYYYMMDD_NNN.

    Args:
        sequence_number: Zero-padded sequence number for the batch.

    Returns:
        A string like "batch_20240115_001".
    """
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"batch_{today}_{sequence_number:03d}"


@dlt.source
def security_logs_source(data_dir: Path = Path("mock_data")):
    """dlt source that reads JSONL files from the data directory.

    Yields both the main security_events resource and the dead_letter resource.

    Args:
        data_dir: Path to directory containing .jsonl files.
    """
    yield security_events_resource(data_dir)
    yield dead_letter_resource(data_dir)


@dlt.resource(write_disposition="merge", primary_key="event_id")
def security_events_resource(data_dir: Path) -> Iterator[dict]:
    """dlt resource yielding validated security events with metadata.

    Reads all .jsonl files from data_dir, validates each record,
    and enriches valid records with metadata columns:
    - _ingested_at: UTC timestamp of ingestion
    - _source_file: path to the source file
    - _batch_id: batch identifier in format batch_YYYYMMDD_NNN

    Invalid records are skipped here and handled by dead_letter_resource.

    Args:
        data_dir: Path to directory containing .jsonl files.

    Yields:
        Validated and enriched security event dictionaries.
    """
    data_path = Path(data_dir)
    jsonl_files = sorted(data_path.glob("*.jsonl"))

    if not jsonl_files:
        logger.warning(
            "No JSONL files found in data directory",
            extra={"context": {"data_dir": str(data_path)}},
        )
        return

    logger.info(
        "Starting security events ingestion",
        extra={"context": {"file_count": len(jsonl_files), "data_dir": str(data_path)}},
    )

    for seq_num, file_path in enumerate(jsonl_files, start=1):
        batch_id = _generate_batch_id(seq_num)
        ingested_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Processing file",
            extra={"context": {"file": str(file_path), "batch_id": batch_id}},
        )

        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.warning(
                        "Failed to parse JSON line",
                        extra={
                            "context": {
                                "file": str(file_path),
                                "line": line_num,
                                "error": str(e),
                            }
                        },
                    )
                    continue

                is_valid, errors = validate_record(record)

                if is_valid:
                    # Enrich with metadata
                    record["_ingested_at"] = ingested_at
                    record["_source_file"] = str(file_path)
                    record["_batch_id"] = batch_id
                    yield record


@dlt.resource(write_disposition="append", name="dead_letter_events")
def dead_letter_resource(data_dir: Path) -> Iterator[dict]:
    """dlt resource yielding invalid records to the dead letter table.

    Reads all .jsonl files from data_dir and routes records that fail
    validation to the dead_letter_events table.

    Dead letter records contain:
    - event_id: from the original record if available, else "unknown"
    - raw_record: the original JSON string
    - error_reason: joined validation error messages
    - rejected_at: UTC timestamp of rejection
    - _source_file: path to the source file
    - _batch_id: batch identifier

    Args:
        data_dir: Path to directory containing .jsonl files.

    Yields:
        Dead letter record dictionaries for invalid events.
    """
    data_path = Path(data_dir)
    jsonl_files = sorted(data_path.glob("*.jsonl"))

    if not jsonl_files:
        return

    for seq_num, file_path in enumerate(jsonl_files, start=1):
        batch_id = _generate_batch_id(seq_num)
        rejected_at = datetime.now(timezone.utc).isoformat()

        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    # JSON parse failures are also dead letters
                    yield {
                        "event_id": "unknown",
                        "raw_record": line,
                        "error_reason": f"JSON parse error: {e}",
                        "rejected_at": rejected_at,
                        "_source_file": str(file_path),
                        "_batch_id": batch_id,
                    }
                    continue

                is_valid, errors = validate_record(record)

                if not is_valid:
                    yield {
                        "event_id": record.get("event_id", "unknown"),
                        "raw_record": json.dumps(record),
                        "error_reason": "; ".join(errors),
                        "rejected_at": rejected_at,
                        "_source_file": str(file_path),
                        "_batch_id": batch_id,
                    }
