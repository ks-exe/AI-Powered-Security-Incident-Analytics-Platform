"""Property-based tests for DLT Pipeline (Properties 5-7).

Validates that the DLT ingestion pipeline preserves source fields,
adds metadata, routes invalid records to dead letter, and is idempotent.

Validates: Requirements 3.2, 3.3, 3.4, 3.7
"""

import json
import shutil
import tempfile
from pathlib import Path

import duckdb
import pytest

from dlt_pipeline.pipeline import run_ingestion
from mock_data.generator import GeneratorConfig, generate_security_events, write_events


@pytest.mark.property
class TestProperty5IngestionPreservesFieldsAndAddsMetadata:
    """Property 5: Ingestion preserves source fields and adds metadata.

    All original fields should be unchanged in DuckDB, and _ingested_at,
    _source_file, _batch_id should be non-null and correctly formatted.
    """

    def test_original_fields_preserved_after_ingestion(self):
        """All source record fields should exist unchanged in DuckDB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            db_path = Path(tmpdir) / "test.duckdb"

            # Generate small dataset
            config = GeneratorConfig(count=50, seed=42, output_dir=source_dir, output_formats=["jsonl"])
            events = generate_security_events(config)
            write_events(events, config)

            # Run ingestion
            result = run_ingestion(source_dir=source_dir, database_path=db_path)

            # Query DuckDB
            conn = duckdb.connect(str(db_path), read_only=True)
            try:
                rows = conn.execute("SELECT * FROM security_bronze.security_events_resource").fetchall()
                columns = [desc[0] for desc in conn.description]

                assert len(rows) >= 50

                # Verify key source fields exist
                expected_fields = ["event_id", "event_time", "username", "src_ip",
                                   "hostname", "event_type", "severity", "status",
                                   "country", "operating_system", "department"]
                for field in expected_fields:
                    assert field in columns, f"Missing field: {field}"
            finally:
                conn.close()

            # Clean up dlt state
            dlt_dir = Path(tmpdir) / "source" / ".dlt"
            if dlt_dir.exists():
                shutil.rmtree(dlt_dir)

    def test_metadata_columns_non_null(self):
        """_ingested_at, _source_file, _batch_id should be non-null for all records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            db_path = Path(tmpdir) / "test.duckdb"

            config = GeneratorConfig(count=30, seed=99, output_dir=source_dir, output_formats=["jsonl"])
            events = generate_security_events(config)
            write_events(events, config)

            run_ingestion(source_dir=source_dir, database_path=db_path)

            conn = duckdb.connect(str(db_path), read_only=True)
            try:
                null_count = conn.execute("""
                    SELECT COUNT(*) FROM security_bronze.security_events_resource
                    WHERE _ingested_at IS NULL OR _source_file IS NULL OR _batch_id IS NULL
                """).fetchone()[0]
                assert null_count == 0, f"Found {null_count} rows with null metadata"

                # Verify batch_id format
                batch_ids = conn.execute(
                    "SELECT DISTINCT _batch_id FROM security_bronze.security_events_resource"
                ).fetchall()
                for (bid,) in batch_ids:
                    assert bid.startswith("batch_"), f"Invalid batch_id format: {bid}"
                    parts = bid.split("_")
                    assert len(parts) == 3, f"batch_id should have 3 parts: {bid}"
            finally:
                conn.close()


@pytest.mark.property
class TestProperty6InvalidRecordsRouteToDeadLetter:
    """Property 6: Invalid records route to dead letter table.

    Records missing required fields should go to dead_letter_events,
    valid records should go to security_events_resource.
    """

    def test_invalid_records_in_dead_letter(self):
        """Records with missing fields should appear in dead_letter_events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            db_path = Path(tmpdir) / "test.duckdb"

            # Create JSONL with mix of valid and invalid records
            valid_records = [
                {
                    "event_id": f"a1b2c3d4-e5f6-4890-abcd-ef12345678{i:02d}",
                    "event_time": "2024-01-15T14:32:07Z",
                    "event_type": "failed_login",
                    "username": "user1",
                    "src_ip": "192.168.1.1",
                    "hostname": "WS-IT-001",
                    "severity": "high",
                    "status": "failure",
                    "country": "US",
                    "operating_system": "Windows 11",
                    "department": "IT",
                }
                for i in range(10)
            ]

            invalid_records = [
                # Missing event_id
                {"event_time": "2024-01-15T14:32:07Z", "event_type": "failed_login",
                 "username": "u1", "src_ip": "1.1.1.1", "hostname": "h1",
                 "severity": "low", "status": "failure", "country": "US",
                 "operating_system": "W11", "department": "IT"},
                # Missing event_type
                {"event_id": "b1b2c3d4-e5f6-4890-abcd-ef1234567800",
                 "event_time": "2024-01-15T14:32:07Z",
                 "username": "u2", "src_ip": "1.1.1.2", "hostname": "h2",
                 "severity": "low", "status": "failure", "country": "US",
                 "operating_system": "W11", "department": "IT"},
                # Invalid event_type value
                {"event_id": "c1b2c3d4-e5f6-4890-abcd-ef1234567800",
                 "event_time": "2024-01-15T14:32:07Z", "event_type": "invalid_type",
                 "username": "u3", "src_ip": "1.1.1.3", "hostname": "h3",
                 "severity": "low", "status": "failure", "country": "US",
                 "operating_system": "W11", "department": "IT"},
            ]

            jsonl_path = source_dir / "test_events.jsonl"
            with open(jsonl_path, "w") as f:
                for record in valid_records + invalid_records:
                    f.write(json.dumps(record) + "\n")
                # Add an invalid JSON line
                f.write("this is not json\n")

            run_ingestion(source_dir=source_dir, database_path=db_path)

            conn = duckdb.connect(str(db_path), read_only=True)
            try:
                # Valid records should be in the main table
                valid_count = conn.execute(
                    "SELECT COUNT(*) FROM security_bronze.security_events_resource"
                ).fetchone()[0]
                assert valid_count == 10, f"Expected 10 valid records, got {valid_count}"

                # Invalid records should be in dead letter
                dead_count = conn.execute(
                    "SELECT COUNT(*) FROM security_bronze.dead_letter_events"
                ).fetchone()[0]
                assert dead_count == 4, f"Expected 4 dead letter records, got {dead_count}"
            finally:
                conn.close()


@pytest.mark.property
class TestProperty7PipelineIdempotency:
    """Property 7: Pipeline idempotency.

    Running N times with same input produces same record count as running once.
    """

    def test_rerun_does_not_duplicate_records(self):
        """Running ingestion twice with same data should not create duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            db_path = Path(tmpdir) / "test.duckdb"

            config = GeneratorConfig(count=50, seed=123, output_dir=source_dir, output_formats=["jsonl"])
            events = generate_security_events(config)
            write_events(events, config)

            # First run
            result1 = run_ingestion(source_dir=source_dir, database_path=db_path)
            count_after_first = result1.records_ingested

            # Second run with same data
            result2 = run_ingestion(source_dir=source_dir, database_path=db_path)
            count_after_second = result2.records_ingested

            assert count_after_first == count_after_second, (
                f"Record count changed: {count_after_first} -> {count_after_second}"
            )

    def test_three_runs_same_count(self):
        """Running ingestion three times produces the same record count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            db_path = Path(tmpdir) / "test.duckdb"

            config = GeneratorConfig(count=30, seed=456, output_dir=source_dir, output_formats=["jsonl"])
            events = generate_security_events(config)
            write_events(events, config)

            counts = []
            for _ in range(3):
                result = run_ingestion(source_dir=source_dir, database_path=db_path)
                counts.append(result.records_ingested)

            assert counts[0] == counts[1] == counts[2], (
                f"Record counts differ across runs: {counts}"
            )
