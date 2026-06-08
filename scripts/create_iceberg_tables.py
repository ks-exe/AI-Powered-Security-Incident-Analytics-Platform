"""Create and register Iceberg tables in Nessie catalog.

This script creates Apache Iceberg tables matching the medallion architecture
layers (bronze, silver, gold) and registers them in the Nessie catalog service.
"""

import os
import sys

from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    FloatType,
    IntegerType,
    NestedField,
    StringType,
    TimestampType,
)


def get_catalog():
    """Load the Nessie catalog configured for MinIO storage."""
    nessie_uri = os.environ.get("NESSIE_URI", "http://localhost:19120/api/v1")
    minio_endpoint = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
    minio_access_key = os.environ.get("MINIO_ROOT_USER", "minioadmin")
    minio_secret_key = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin123")

    catalog = load_catalog(
        "nessie",
        **{
            "type": "rest",
            "uri": nessie_uri,
            "s3.endpoint": minio_endpoint,
            "s3.access-key-id": minio_access_key,
            "s3.secret-access-key": minio_secret_key,
            "s3.path-style-access": "true",
        },
    )
    return catalog


# ─── Schema Definitions ──────────────────────────────────────────────────────

BRONZE_SCHEMA = Schema(
    NestedField(1, "event_id", StringType(), required=True),
    NestedField(2, "event_time", TimestampType(), required=True),
    NestedField(3, "username", StringType(), required=True),
    NestedField(4, "src_ip", StringType(), required=True),
    NestedField(5, "destination_ip", StringType(), required=False),
    NestedField(6, "hostname", StringType(), required=True),
    NestedField(7, "event_type", StringType(), required=True),
    NestedField(8, "severity", StringType(), required=True),
    NestedField(9, "status", StringType(), required=True),
    NestedField(10, "country", StringType(), required=True),
    NestedField(11, "operating_system", StringType(), required=True),
    NestedField(12, "department", StringType(), required=True),
    NestedField(13, "detection_time", TimestampType(), required=False),
    NestedField(14, "resolution_time", TimestampType(), required=False),
    NestedField(15, "_ingested_at", TimestampType(), required=True),
    NestedField(16, "_source_file", StringType(), required=True),
    NestedField(17, "_batch_id", StringType(), required=True),
)

SILVER_SCHEMA = Schema(
    NestedField(1, "event_id", StringType(), required=True),
    NestedField(2, "event_time", TimestampType(), required=True),
    NestedField(3, "detection_time", TimestampType(), required=False),
    NestedField(4, "resolution_time", TimestampType(), required=False),
    NestedField(5, "username", StringType(), required=True),
    NestedField(6, "src_ip", StringType(), required=True),
    NestedField(7, "destination_ip", StringType(), required=False),
    NestedField(8, "hostname", StringType(), required=True),
    NestedField(9, "event_type", StringType(), required=True),
    NestedField(10, "severity", StringType(), required=True),
    NestedField(11, "severity_rank", IntegerType(), required=True),
    NestedField(12, "status", StringType(), required=True),
    NestedField(13, "country", StringType(), required=True),
    NestedField(14, "operating_system", StringType(), required=True),
    NestedField(15, "department", StringType(), required=True),
    NestedField(16, "hour_of_day", IntegerType(), required=True),
    NestedField(17, "day_of_week", IntegerType(), required=True),
    NestedField(18, "is_business_hours", BooleanType(), required=True),
    NestedField(19, "is_internal_ip", BooleanType(), required=True),
    NestedField(20, "is_attack_event", BooleanType(), required=True),
    NestedField(21, "_ingested_at", TimestampType(), required=True),
    NestedField(22, "_source_file", StringType(), required=True),
    NestedField(23, "_batch_id", StringType(), required=True),
)

GOLD_KPI_SCHEMA = Schema(
    NestedField(1, "total_attacks", IntegerType(), required=True),
    NestedField(2, "failed_login_rate", FloatType(), required=False),
    NestedField(3, "avg_mttd_minutes", FloatType(), required=False),
    NestedField(4, "avg_mttr_minutes", FloatType(), required=False),
    NestedField(5, "sla_compliance", FloatType(), required=False),
    NestedField(6, "computed_at", TimestampType(), required=True),
)

GOLD_ATTACK_BY_DAY_SCHEMA = Schema(
    NestedField(1, "event_date", StringType(), required=True),
    NestedField(2, "attack_count", IntegerType(), required=True),
    NestedField(3, "cumulative_attack_count", IntegerType(), required=True),
)

GOLD_ATTACK_BY_COUNTRY_SCHEMA = Schema(
    NestedField(1, "country", StringType(), required=True),
    NestedField(2, "attack_count", IntegerType(), required=True),
    NestedField(3, "percentage_of_total", FloatType(), required=True),
)

GOLD_HOURLY_SUMMARY_SCHEMA = Schema(
    NestedField(1, "event_hour", TimestampType(), required=True),
    NestedField(2, "event_type", StringType(), required=True),
    NestedField(3, "event_count", IntegerType(), required=True),
    NestedField(4, "unique_ips", IntegerType(), required=True),
    NestedField(5, "unique_users", IntegerType(), required=True),
)

GOLD_ANOMALY_RESULTS_SCHEMA = Schema(
    NestedField(1, "window_start", TimestampType(), required=True),
    NestedField(2, "window_end", TimestampType(), required=True),
    NestedField(3, "anomaly_score", FloatType(), required=True),
    NestedField(4, "is_anomaly", BooleanType(), required=True),
    NestedField(5, "total_event_count", IntegerType(), required=True),
    NestedField(6, "top_contributing_feature", StringType(), required=False),
    NestedField(7, "model_version", StringType(), required=True),
)


# ─── Table Definitions ────────────────────────────────────────────────────────

TABLES = {
    "bronze.raw_security_events": {
        "schema": BRONZE_SCHEMA,
        "location": "s3://bronze-layer/raw_security_events",
    },
    "bronze.dead_letter_events": {
        "schema": Schema(
            NestedField(1, "event_id", StringType(), required=False),
            NestedField(2, "raw_record", StringType(), required=True),
            NestedField(3, "error_reason", StringType(), required=True),
            NestedField(4, "rejected_at", TimestampType(), required=True),
            NestedField(5, "_source_file", StringType(), required=True),
            NestedField(6, "_batch_id", StringType(), required=True),
        ),
        "location": "s3://bronze-layer/dead_letter_events",
    },
    "silver.silver_events": {
        "schema": SILVER_SCHEMA,
        "location": "s3://silver-layer/silver_events",
    },
    "gold.kpi_summary": {
        "schema": GOLD_KPI_SCHEMA,
        "location": "s3://gold-layer/kpi_summary",
    },
    "gold.attack_volume_by_day": {
        "schema": GOLD_ATTACK_BY_DAY_SCHEMA,
        "location": "s3://gold-layer/attack_volume_by_day",
    },
    "gold.attack_volume_by_country": {
        "schema": GOLD_ATTACK_BY_COUNTRY_SCHEMA,
        "location": "s3://gold-layer/attack_volume_by_country",
    },
    "gold.hourly_event_summary": {
        "schema": GOLD_HOURLY_SUMMARY_SCHEMA,
        "location": "s3://gold-layer/hourly_event_summary",
    },
    "gold.anomaly_results": {
        "schema": GOLD_ANOMALY_RESULTS_SCHEMA,
        "location": "s3://gold-layer/anomaly_results",
    },
}


def create_namespaces(catalog):
    """Create namespaces for each medallion layer."""
    namespaces = ["bronze", "silver", "gold"]
    for ns in namespaces:
        try:
            catalog.create_namespace(ns)
            print(f"  Created namespace: {ns}")
        except Exception:
            print(f"  Namespace already exists: {ns}")


def create_tables(catalog):
    """Create all Iceberg tables in the Nessie catalog."""
    for table_name, config in TABLES.items():
        namespace, name = table_name.split(".")
        identifier = (namespace, name)
        try:
            catalog.create_table(
                identifier=identifier,
                schema=config["schema"],
                location=config["location"],
            )
            print(f"  Created table: {table_name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  Table already exists: {table_name}")
            else:
                print(f"  Error creating {table_name}: {e}")


def main():
    """Main entry point for Iceberg table creation."""
    print("=" * 60)
    print("Iceberg Table Creation and Registration")
    print("=" * 60)

    print("\nConnecting to Nessie catalog...")
    try:
        catalog = get_catalog()
    except Exception as e:
        print(f"ERROR: Failed to connect to Nessie catalog: {e}")
        print("Make sure Nessie is running on port 19120")
        sys.exit(1)

    print("\nCreating namespaces...")
    create_namespaces(catalog)

    print("\nCreating Iceberg tables...")
    create_tables(catalog)

    print("\n" + "=" * 60)
    print("Table registration complete.")
    print("Tables support schema evolution without data rewrite.")
    print("=" * 60)


if __name__ == "__main__":
    main()
