"""DLT pipeline execution for security log ingestion.

Implements the run_ingestion() function that executes the DLT pipeline,
loading security events into DuckDB with incremental loading and idempotency.

Requirements: 3.5, 3.6, 3.7, 3.8
"""

import time
from dataclasses import dataclass
from pathlib import Path

import dlt
import duckdb
import yaml

from dlt_pipeline.sources import security_logs_source
from scripts.logging_config import get_logger

logger = get_logger("dlt_pipeline")


def _load_config() -> dict:
    """Load pipeline configuration from config.yaml.

    Returns:
        Dictionary with pipeline configuration values.
    """
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


@dataclass
class IngestionResult:
    """Result of a pipeline ingestion run.

    Attributes:
        records_ingested: Number of valid records loaded into the Bronze layer.
        records_rejected: Number of invalid records routed to dead letter table.
        elapsed_seconds: Total time taken for the ingestion run.
        records_per_second: Throughput metric (records_ingested / elapsed_seconds).
        batch_id: Identifier for this ingestion batch.
    """

    records_ingested: int
    records_rejected: int
    elapsed_seconds: float
    records_per_second: float
    batch_id: str


def run_ingestion(
    source_dir: Path = Path("mock_data"),
    destination: str = "duckdb",
    database_path: Path = Path("data/security_analytics.duckdb"),
) -> IngestionResult:
    """Execute the DLT ingestion pipeline.

    Creates a dlt pipeline with pipeline_name="security_ingestion" and
    DuckDB destination. Uses the security_logs_source to read JSONL files,
    validate records, and load them into the Bronze layer.

    Supports incremental loading via dlt state management.
    Idempotent: re-running with same data produces no duplicates
    (achieved via write_disposition="merge" with primary_key="event_id"
    in the source resource definition).

    Args:
        source_dir: Path to directory containing .jsonl source files.
        destination: Destination type (currently only "duckdb" supported).
        database_path: Path to the DuckDB database file.

    Returns:
        IngestionResult with metrics about the completed ingestion.
    """
    config = _load_config()
    pipeline_name = config.get("pipeline", {}).get("name", "security_ingestion")
    dataset_name = config.get("pipeline", {}).get("dataset_name", "security_bronze")

    logger.info(
        "Starting DLT ingestion pipeline",
        extra={
            "context": {
                "pipeline_name": pipeline_name,
                "source_dir": str(source_dir),
                "destination": destination,
                "database_path": str(database_path),
            }
        },
    )

    # Ensure the database directory exists
    database_path.parent.mkdir(parents=True, exist_ok=True)

    # Create the dlt pipeline
    pipeline = dlt.pipeline(
        pipeline_name=pipeline_name,
        destination=dlt.destinations.duckdb(str(database_path)),
        dataset_name=dataset_name,
    )

    # Create the source
    source = security_logs_source(data_dir=source_dir)

    # Track timing
    start_time = time.time()

    # Run the pipeline
    load_info = pipeline.run(source)

    elapsed_seconds = time.time() - start_time

    # Query the database to get actual record counts
    records_ingested = _count_table_rows(database_path, dataset_name, "security_events_resource")
    records_rejected = _count_table_rows(database_path, dataset_name, "dead_letter_events")

    # Calculate throughput
    records_per_second = records_ingested / elapsed_seconds if elapsed_seconds > 0 else 0.0

    # Generate batch_id from load info
    batch_id = str(load_info.loads_ids[0]) if load_info.loads_ids else "unknown"

    result = IngestionResult(
        records_ingested=records_ingested,
        records_rejected=records_rejected,
        elapsed_seconds=round(elapsed_seconds, 2),
        records_per_second=round(records_per_second, 2),
        batch_id=batch_id,
    )

    # Log completion metrics
    logger.info(
        "DLT ingestion pipeline completed",
        extra={
            "context": {
                "records_ingested": result.records_ingested,
                "records_rejected": result.records_rejected,
                "elapsed_seconds": result.elapsed_seconds,
                "records_per_second": result.records_per_second,
                "batch_id": result.batch_id,
            }
        },
    )

    return result


def _count_table_rows(database_path: Path, dataset_name: str, table_name: str) -> int:
    """Count the number of rows in a DuckDB table.

    Args:
        database_path: Path to the DuckDB database file.
        dataset_name: Schema/dataset name in DuckDB.
        table_name: Table name to count rows for.

    Returns:
        Number of rows in the table, or 0 if table doesn't exist.
    """
    try:
        conn = duckdb.connect(str(database_path), read_only=True)
        try:
            result = conn.execute(
                f"SELECT COUNT(*) FROM {dataset_name}.{table_name}"
            ).fetchone()
            return result[0] if result else 0
        except duckdb.CatalogException:
            # Table doesn't exist yet
            return 0
        finally:
            conn.close()
    except Exception as e:
        logger.warning(
            "Failed to count table rows",
            extra={
                "context": {
                    "table": f"{dataset_name}.{table_name}",
                    "error": str(e),
                }
            },
        )
        return 0


if __name__ == "__main__":
    """Allow running as: python -m dlt_pipeline.pipeline"""
    config = _load_config()

    source_dir = Path(
        config.get("source", {}).get("data_dir", "mock_data")
    )
    dest = config.get("pipeline", {}).get("destination", "duckdb")
    db_path = Path(
        config.get("destination", {}).get("database_path", "data/security_analytics.duckdb")
    )

    result = run_ingestion(
        source_dir=source_dir,
        destination=dest,
        database_path=db_path,
    )

    print(f"Ingestion complete:")
    print(f"  Records ingested: {result.records_ingested}")
    print(f"  Records rejected: {result.records_rejected}")
    print(f"  Elapsed seconds:  {result.elapsed_seconds}")
    print(f"  Records/second:   {result.records_per_second}")
    print(f"  Batch ID:         {result.batch_id}")
