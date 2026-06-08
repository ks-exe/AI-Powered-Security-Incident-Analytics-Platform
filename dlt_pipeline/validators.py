"""Record validation logic for the DLT ingestion pipeline.

Validates security event records before ingestion into the Bronze layer.
Invalid records are routed to the dead_letter_events table.

Requirements: 3.4
"""

# The 8 accepted event_type values
ACCEPTED_EVENT_TYPES = frozenset({
    "failed_login",
    "successful_login",
    "malware_alert",
    "privilege_escalation",
    "suspicious_ip_activity",
    "vpn_login",
    "account_lockout",
    "brute_force_attempt",
})

# Required fields that must be present and non-empty
REQUIRED_FIELDS = ("event_id", "event_time", "event_type")


def validate_record(record: dict) -> tuple[bool, list[str]]:
    """Validate a security event record.

    Returns (is_valid, list_of_error_messages).
    Required fields: event_id, event_time, event_type.
    Validates event_type is one of the 8 accepted values.

    Args:
        record: A dictionary representing a security event record.

    Returns:
        A tuple of (is_valid, errors) where is_valid is True if the record
        passes all validation checks, and errors is a list of error messages
        describing any validation failures.
    """
    errors: list[str] = []

    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value is None:
            errors.append(f"Missing required field: {field}")
        elif isinstance(value, str) and value.strip() == "":
            errors.append(f"Required field is empty: {field}")

    # Only validate event_type value if the field is present and non-empty
    event_type = record.get("event_type")
    if event_type is not None and (not isinstance(event_type, str) or event_type.strip() != ""):
        if event_type not in ACCEPTED_EVENT_TYPES:
            errors.append(
                f"Invalid event_type: '{event_type}'. "
                f"Must be one of: {sorted(ACCEPTED_EVENT_TYPES)}"
            )

    is_valid = len(errors) == 0
    return is_valid, errors
