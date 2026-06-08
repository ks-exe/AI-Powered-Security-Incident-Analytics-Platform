"""Unit tests for DLT Pipeline record validator.

Tests validate_record() function for required field presence,
non-empty checks, and event_type validation against accepted values.

Requirements: 3.4
"""

import pytest

from dlt_pipeline.validators import (
    ACCEPTED_EVENT_TYPES,
    REQUIRED_FIELDS,
    validate_record,
)


def _make_valid_record(**overrides) -> dict:
    """Create a valid security event record with optional field overrides."""
    record = {
        "event_id": "a1b2c3d4-e5f6-4890-abcd-ef1234567890",
        "event_time": "2024-01-15T14:32:07Z",
        "event_type": "failed_login",
        "username": "john.smith",
        "src_ip": "192.168.1.105",
        "hostname": "WS-FIN-042",
        "severity": "high",
        "status": "failure",
        "country": "US",
        "operating_system": "Windows 11",
        "department": "Finance",
    }
    record.update(overrides)
    return record


@pytest.mark.unit
class TestValidateRecordValidInputs:
    """Test validate_record with valid records."""

    def test_valid_record_returns_true_no_errors(self):
        """A complete valid record should pass validation."""
        record = _make_valid_record()
        is_valid, errors = validate_record(record)
        assert is_valid is True
        assert errors == []

    def test_all_event_types_accepted(self):
        """Every one of the 8 accepted event_types should pass validation."""
        for event_type in ACCEPTED_EVENT_TYPES:
            record = _make_valid_record(event_type=event_type)
            is_valid, errors = validate_record(record)
            assert is_valid is True, f"event_type '{event_type}' should be valid"
            assert errors == []

    def test_valid_record_with_extra_fields(self):
        """Records with additional fields beyond required ones should still pass."""
        record = _make_valid_record(
            extra_field="extra_value",
            detection_time="2024-01-15T14:35:22Z",
        )
        is_valid, errors = validate_record(record)
        assert is_valid is True
        assert errors == []

    def test_valid_record_with_non_string_event_time(self):
        """event_time as a non-string value (e.g., datetime) should pass if not empty."""
        from datetime import datetime, timezone

        record = _make_valid_record(
            event_time=datetime(2024, 1, 15, 14, 32, 7, tzinfo=timezone.utc)
        )
        is_valid, errors = validate_record(record)
        assert is_valid is True
        assert errors == []


@pytest.mark.unit
class TestValidateRecordMissingFields:
    """Test validate_record detects missing required fields."""

    def test_missing_event_id(self):
        """Record without event_id should fail validation."""
        record = _make_valid_record()
        del record["event_id"]
        is_valid, errors = validate_record(record)
        assert is_valid is False
        assert any("event_id" in e for e in errors)

    def test_missing_event_time(self):
        """Record without event_time should fail validation."""
        record = _make_valid_record()
        del record["event_time"]
        is_valid, errors = validate_record(record)
        assert is_valid is False
        assert any("event_time" in e for e in errors)

    def test_missing_event_type(self):
        """Record without event_type should fail validation."""
        record = _make_valid_record()
        del record["event_type"]
        is_valid, errors = validate_record(record)
        assert is_valid is False
        assert any("event_type" in e for e in errors)

    def test_missing_all_required_fields(self):
        """Record missing all required fields should report all errors."""
        record = {"username": "john", "src_ip": "192.168.1.1"}
        is_valid, errors = validate_record(record)
        assert is_valid is False
        assert len(errors) == 3
        for field in REQUIRED_FIELDS:
            assert any(field in e for e in errors)

    def test_none_value_for_required_field(self):
        """A required field explicitly set to None should fail validation."""
        record = _make_valid_record(event_id=None)
        is_valid, errors = validate_record(record)
        assert is_valid is False
        assert any("event_id" in e for e in errors)


@pytest.mark.unit
class TestValidateRecordEmptyFields:
    """Test validate_record detects empty required fields."""

    def test_empty_string_event_id(self):
        """event_id as empty string should fail validation."""
        record = _make_valid_record(event_id="")
        is_valid, errors = validate_record(record)
        assert is_valid is False
        assert any("event_id" in e for e in errors)

    def test_whitespace_only_event_id(self):
        """event_id containing only whitespace should fail validation."""
        record = _make_valid_record(event_id="   ")
        is_valid, errors = validate_record(record)
        assert is_valid is False
        assert any("event_id" in e for e in errors)

    def test_empty_string_event_time(self):
        """event_time as empty string should fail validation."""
        record = _make_valid_record(event_time="")
        is_valid, errors = validate_record(record)
        assert is_valid is False
        assert any("event_time" in e for e in errors)

    def test_empty_string_event_type(self):
        """event_type as empty string should fail validation."""
        record = _make_valid_record(event_type="")
        is_valid, errors = validate_record(record)
        assert is_valid is False
        assert any("event_type" in e for e in errors)


@pytest.mark.unit
class TestValidateRecordInvalidEventType:
    """Test validate_record detects invalid event_type values."""

    def test_invalid_event_type(self):
        """An unrecognized event_type should fail validation."""
        record = _make_valid_record(event_type="unknown_event")
        is_valid, errors = validate_record(record)
        assert is_valid is False
        assert any("event_type" in e and "unknown_event" in e for e in errors)

    def test_event_type_case_sensitive(self):
        """event_type validation is case-sensitive: 'Failed_Login' is invalid."""
        record = _make_valid_record(event_type="Failed_Login")
        is_valid, errors = validate_record(record)
        assert is_valid is False
        assert any("event_type" in e for e in errors)

    def test_event_type_with_extra_whitespace(self):
        """event_type with leading/trailing whitespace is invalid."""
        record = _make_valid_record(event_type=" failed_login ")
        is_valid, errors = validate_record(record)
        assert is_valid is False
        assert any("event_type" in e for e in errors)

    def test_event_type_typo(self):
        """A common typo in event_type should fail validation."""
        record = _make_valid_record(event_type="brute_force")
        is_valid, errors = validate_record(record)
        assert is_valid is False
        assert any("event_type" in e for e in errors)


@pytest.mark.unit
class TestValidateRecordMultipleErrors:
    """Test validate_record reports multiple errors simultaneously."""

    def test_missing_field_and_invalid_event_type(self):
        """Missing event_id + invalid event_type should produce 2 errors."""
        record = _make_valid_record(event_type="invalid_type")
        del record["event_id"]
        is_valid, errors = validate_record(record)
        assert is_valid is False
        assert len(errors) == 2
        assert any("event_id" in e for e in errors)
        assert any("event_type" in e for e in errors)

    def test_empty_record(self):
        """An empty dict should report all 3 required field errors."""
        is_valid, errors = validate_record({})
        assert is_valid is False
        assert len(errors) == 3


@pytest.mark.unit
class TestValidateRecordReturnType:
    """Test validate_record returns correct types."""

    def test_returns_tuple(self):
        """validate_record should return a tuple."""
        result = validate_record(_make_valid_record())
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_first_element_is_bool(self):
        """First element of the result should be a bool."""
        is_valid, _ = validate_record(_make_valid_record())
        assert isinstance(is_valid, bool)

    def test_second_element_is_list_of_strings(self):
        """Second element should be a list of strings."""
        _, errors = validate_record(_make_valid_record())
        assert isinstance(errors, list)

        # Check error list contains strings when there are errors
        record = _make_valid_record()
        del record["event_id"]
        _, errors = validate_record(record)
        assert all(isinstance(e, str) for e in errors)


@pytest.mark.unit
class TestAcceptedEventTypes:
    """Test the ACCEPTED_EVENT_TYPES constant."""

    def test_exactly_8_accepted_event_types(self):
        """There should be exactly 8 accepted event types."""
        assert len(ACCEPTED_EVENT_TYPES) == 8

    def test_expected_event_types_present(self):
        """All 8 expected event types should be in ACCEPTED_EVENT_TYPES."""
        expected = {
            "failed_login",
            "successful_login",
            "malware_alert",
            "privilege_escalation",
            "suspicious_ip_activity",
            "vpn_login",
            "account_lockout",
            "brute_force_attempt",
        }
        assert ACCEPTED_EVENT_TYPES == expected
