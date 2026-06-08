"""Integration tests for DLT Pipeline.

End-to-end tests verifying the complete ingestion flow from JSONL files
into DuckDB, including metadata enrichment, dead letter routing, and idempotency.

Requirements: 3.1, 3.5, 3.7
"""

import json
import tempfile
from pathlib import Path

import duckdb
import pytest

from dlt_pipeline.pipeline import IngestionResult, run_ingestion
from mock_data.generator import GeneratorConfig, generate_security_events, write_events


@pytest.mark.integration
class TestEndToEndIngestion:
    """Test full end-to-end ingestion of JSONL into DuckDB."""

    def test_ingestion_loads_all_valid_records(self):
        """All valid records from a JSONL file should be loaded into DuckDB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            db_path = Path(tmpdir) / "test.duckdb"

            # Generate known dataset
            config = GeneratorConfig(
                count=100, seed=42, output_dir=source_dir, output_formats=["jsonl"]
            )
            events = generate_security_events(config)
            write_events(events, config)

            # Count lines in JSONL
            jsonl_file = source_dir / "security_events.jsonl"
            with open(jsonl_file) as f:
                line_count = sum(1 for line in f if line.strip())

            # Run ingestion
            result = run_ingestion(source_dir=source_dir, database_path=db_path)

            # Record count should match source file lines
            assert result.records_ingested == line_count
            assert isinstance(result, IngestionResult)
            assert result.elapsed_seconds > 0
            assert result.records_per_second > 0

    def test_ingestion_result_metrics(self):
        """IngestionResult should have all metrics populated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            db_path = Path(tmpdir) / "test.duckdb"

            config = GeneratorConfig(
                count=50, seed=77, output_dir=source_dir, output_formats=["jsonl"]
            )
            events = generate_security_events(config)
            write_events(events, config)

            result = run_ingestion(source_dir=source_dir, database_path=db_path)

            assert result.records_ingested > 0
            assert result.records_rejected >= 0
            assert result.elapsed_seconds > 0
            assert result.records_per_second > 0
            assert result.batch_id != "unknown"


@pytest.mark.integration
class TestMetadataColumns:
    """Verify metadata columns are populated correctly."""

    def test_ingested_at_is_populated(self):
        """_ingested_at column should be non-null ISO timestamp for all records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            db_path = Path(tmpdir) / "test.duckdb"

            config = GeneratorConfig(
                count=20, seed=11, output_dir=source_dir, output_formats=["jsonl"]
            )
            events = generate_security_events(config)
            write_events(events, config)

            run_ingestion(source_dir=source_dir, database_path=db_path)

            conn = duckdb.connect(str(db_path), read_only=True)
            try:
                null_count = conn.execute("""
                    SELECT COUNT(*) FROM security_bronze.security_events_resource
                    WHERE _ingested_at IS NULL
                """).fetchone()[0]
                assert null_count == 0
            finally:
                conn.close()

    def test_source_file_is_populated(self):
        """_source_file column should contain the JSONL file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            db_path = Path(tmpdir) / "test.duckdb"

            config = GeneratorConfig(
                count=20, seed=22, output_dir=source_dir, output_formats=["jsonl"]
            )
            events = generate_security_events(config)
            write_events(events, config)

            run_ingestion(source_dir=source_dir, database_path=db_path)

            conn = duckdb.connect(str(db_path), read_only=True)
            try:
                files = conn.execute("""
                    SELECT DISTINCT _source_file FROM security_bronze.security_events_resource
                """).fetchall()
                assert len(files) > 0
                for (f,) in files:
                    assert f is not None
                    assert "security_events.jsonl" in f
            finally:
                conn.close()

    def test_batch_id_format(self):
        """_batch_id should follow format batch_YYYYMMDD_NNN."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            db_path = Path(tmpdir) / "test.duckdb"

            config = GeneratorConfig(
                count=20, seed=33, output_dir=source_dir, output_formats=["jsonl"]
            )
            events = generate_security_events(config)
            write_events(events, config)

            run_ingestion(source_dir=source_dir, database_path=db_path)

            conn = duckdb.connect(str(db_path), read_only=True)
            try:
                batch_ids = conn.execute("""
                    SELECT DISTINCT _batch_id FROM security_bronze.security_events_resource
                """).fetchall()
                assert len(batch_ids) > 0
                for (bid,) in batch_ids:
                    assert bid.startswith("batch_")
                    parts = bid.split("_")
                    assert len(parts) == 3
                    # Date part should be 8 digits
                    assert len(parts[1]) == 8
                    assert parts[1].isdigit()
                    # Sequence part should be 3 digits
                    assert len(parts[2]) == 3
                    assert parts[2].isdigit()
            finally:
                conn.close()


@pytest.mark.integration
class TestDeadLetterRouting:
    """Verify dead letter table captures malformed records."""

    def test_malformed_records_go_to_dead_letter(self):
        """Records with missing required fields should be in dead_letter_events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            db_path = Path(tmpdir) / "test.duckdb"

            # Create file with mix of valid and invalid records
            valid_record = {
                "event_id": "a1b2c3d4-e5f6-4890-abcd-ef1234567890",
                "event_time": "2024-01-15T14:32:07Z",
                "event_type": "failed_login",
                "username": "test_user",
                "src_ip": "192.168.1.1",
                "hostname": "WS-IT-001",
                "severity": "high",
                "status": "failure",
                "country": "US",
                "operating_system": "Windows 11",
                "department": "IT",
            }
            invalid_no_event_id = {
                "event_time": "2024-01-15T14:32:07Z",
                "event_type": "failed_login",
                "username": "bad_user",
                "src_ip": "1.1.1.1",
                "hostname": "h1",
                "severity": "low",
                "status": "failure",
                "country": "US",
                "operating_system": "W11",
                "department": "IT",
            }
            invalid_bad_type = {
                "event_id": "b1b2c3d4-e5f6-4890-abcd-ef1234567890",
                "event_time": "2024-01-15T14:32:07Z",
                "event_type": "not_a_real_type",
                "username": "bad_user2",
                "src_ip": "1.1.1.2",
                "hostname": "h2",
                "severity": "low",
                "status": "failure",
                "country": "US",
                "operating_system": "W11",
                "department": "IT",
            }

            jsonl_path = source_dir / "test.jsonl"
            with open(jsonl_path, "w") as f:
                f.write(json.dumps(valid_record) + "\n")
                f.write(json.dumps(invalid_no_event_id) + "\n")
                f.write(json.dumps(invalid_bad_type) + "\n")

            run_ingestion(source_dir=source_dir, database_path=db_path)

            conn = duckdb.connect(str(db_path), read_only=True)
            try:
                valid_count = conn.execute(
                    "SELECT COUNT(*) FROM security_bronze.security_events_resource"
                ).fetchone()[0]
                dead_count = conn.execute(
                    "SELECT COUNT(*) FROM security_bronze.dead_letter_events"
                ).fetchone()[0]

                assert valid_count == 1
                assert dead_count == 2
            finally:
                conn.close()


@pytest.mark.integration
class TestIdempotency:
    """Verify idempotent re-run does not duplicate records."""

    def test_rerun_same_count(self):
        """Running ingestion twice should produce the same record count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            db_path = Path(tmpdir) / "test.duckdb"

            config = GeneratorConfig(
                count=50, seed=55, output_dir=source_dir, output_formats=["jsonl"]
            )
            events = generate_security_events(config)
            write_events(events, config)

            result1 = run_ingestion(source_dir=source_dir, database_path=db_path)
            result2 = run_ingestion(source_dir=source_dir, database_path=db_path)

            assert result1.records_ingested == result2.records_ingested, (
                f"First run: {result1.records_ingested}, "
                f"Second run: {result2.records_ingested}"
            )
