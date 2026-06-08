"""Iceberg destination for DLT pipeline.

Provides Iceberg write support for the production profile, writing data
to MinIO object storage via Apache Iceberg table format with Nessie catalog.
The MVP profile continues using DuckDB destination.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import dlt


@dataclass
class IcebergConfig:
    """Configuration for Iceberg destination."""

    minio_endpoint: str = field(
        default_factory=lambda: os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
    )
    minio_access_key: str = field(
        default_factory=lambda: os.environ.get("MINIO_ROOT_USER", "minioadmin")
    )
    minio_secret_key: str = field(
        default_factory=lambda: os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin123")
    )
    nessie_uri: str = field(
        default_factory=lambda: os.environ.get("NESSIE_URI", "http://localhost:19120/api/v1")
    )
    bucket_name: str = "bronze-layer"
    catalog_name: str = "nessie"


def get_active_profile() -> str:
    """Determine active profile from environment.

    Returns 'production' if PIPELINE_PROFILE=production, else 'mvp'.
    """
    return os.environ.get("PIPELINE_PROFILE", "mvp").lower()


def create_iceberg_destination(config: IcebergConfig | None = None):
    """Create a DLT filesystem destination configured for Iceberg/MinIO.

    This destination writes Parquet files to MinIO object storage,
    which can then be registered as Iceberg tables via Nessie catalog.

    Args:
        config: Optional IcebergConfig. Uses defaults from environment if None.

    Returns:
        A dlt filesystem destination configured for MinIO/S3.
    """
    if config is None:
        config = IcebergConfig()

    destination = dlt.destinations.filesystem(
        bucket_url=f"s3://{config.bucket_name}",
        credentials={
            "aws_access_key_id": config.minio_access_key,
            "aws_secret_access_key": config.minio_secret_key,
            "endpoint_url": config.minio_endpoint,
            "region_name": "us-east-1",
        },
        layout="{table_name}/{load_id}.{file_id}.{ext}",
    )
    return destination


def create_duckdb_destination(database_path: Path = Path("data/security_analytics.duckdb")):
    """Create a DLT DuckDB destination for the MVP profile.

    Args:
        database_path: Path to the DuckDB database file.

    Returns:
        A dlt DuckDB destination.
    """
    return dlt.destinations.duckdb(str(database_path))


def get_destination(database_path: Path = Path("data/security_analytics.duckdb")):
    """Get the appropriate DLT destination based on active profile.

    Production profile -> MinIO/Iceberg via filesystem destination
    MVP profile -> Local DuckDB

    Args:
        database_path: Path to DuckDB database (used only in MVP profile).

    Returns:
        Configured dlt destination.
    """
    profile = get_active_profile()

    if profile == "production":
        return create_iceberg_destination()
    else:
        return create_duckdb_destination(database_path)


def run_iceberg_pipeline(
    source,
    table_name: str = "raw_security_events",
    write_disposition: str = "merge",
    primary_key: str = "event_id",
):
    """Run a DLT pipeline with Iceberg destination.

    Creates and executes a pipeline writing to MinIO/Iceberg storage.

    Args:
        source: DLT source or resource to ingest.
        table_name: Target table name in Iceberg.
        write_disposition: How to handle existing data (merge, append, replace).
        primary_key: Column used for merge deduplication.

    Returns:
        Pipeline load info with ingestion metrics.
    """
    config = IcebergConfig()

    pipeline = dlt.pipeline(
        pipeline_name="security_iceberg_pipeline",
        destination=create_iceberg_destination(config),
        dataset_name="security_events",
    )

    load_info = pipeline.run(
        source,
        table_name=table_name,
        write_disposition=write_disposition,
        primary_key=primary_key,
    )

    return load_info
