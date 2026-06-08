"""Pydantic schemas for Security Event data validation.

Defines the EventType and Severity enums and the SecurityEvent BaseModel
with field validators for event_id (UUID v4), src_ip (IPv4), and event_time (UTC).
"""

import ipaddress
import re
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# UUID v4 regex pattern
_UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class EventType(str, Enum):
    """Security event type categories."""

    FAILED_LOGIN = "failed_login"
    SUCCESSFUL_LOGIN = "successful_login"
    MALWARE_ALERT = "malware_alert"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    SUSPICIOUS_IP = "suspicious_ip_activity"
    VPN_LOGIN = "vpn_login"
    ACCOUNT_LOCKOUT = "account_lockout"
    BRUTE_FORCE = "brute_force_attempt"


class Severity(str, Enum):
    """Security event severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEvent(BaseModel):
    """Pydantic model representing a single security log event.

    Validates all fields according to the Security_Event schema specification.
    Includes field validators for UUID v4 format, IPv4 addresses, and UTC timestamps.
    """

    event_id: str = Field(..., description="UUID v4 unique identifier for each event")
    event_time: datetime = Field(..., description="When the event occurred (UTC)")
    username: str = Field(..., description="User account associated with event")
    src_ip: str = Field(..., description="Source IPv4 address")
    destination_ip: str | None = Field(None, description="Destination IPv4 address")
    hostname: str = Field(..., description="Machine hostname")
    event_type: EventType = Field(..., description="Category of security event")
    severity: Severity = Field(..., description="Severity level")
    status: str = Field(..., description="Outcome: success, failure, blocked, detected")
    country: str = Field(..., description="Country of origin (ISO 3166-1)")
    operating_system: str = Field(..., description="OS of source machine")
    department: str = Field(..., description="Organizational department")
    detection_time: datetime | None = Field(
        None, description="Simulated time event was detected"
    )
    resolution_time: datetime | None = Field(
        None, description="Simulated time event was resolved"
    )

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        """Validate that event_id is a valid UUID v4 format."""
        if not _UUID_V4_PATTERN.match(v):
            raise ValueError(f"event_id must be a valid UUID v4, got: {v}")
        return v

    @field_validator("src_ip")
    @classmethod
    def validate_src_ip(cls, v: str) -> str:
        """Validate that src_ip is a valid IPv4 address."""
        try:
            addr = ipaddress.IPv4Address(v)
        except (ipaddress.AddressValueError, ValueError) as e:
            raise ValueError(f"src_ip must be a valid IPv4 address, got: {v}") from e
        return str(addr)

    @field_validator("destination_ip")
    @classmethod
    def validate_destination_ip(cls, v: str | None) -> str | None:
        """Validate that destination_ip is a valid IPv4 address if provided."""
        if v is None:
            return v
        try:
            addr = ipaddress.IPv4Address(v)
        except (ipaddress.AddressValueError, ValueError) as e:
            raise ValueError(f"destination_ip must be a valid IPv4 address, got: {v}") from e
        return str(addr)

    @field_validator("event_time")
    @classmethod
    def validate_event_time(cls, v: datetime) -> datetime:
        """Validate that event_time is timezone-aware (UTC)."""
        if v.tzinfo is None:
            # Assume UTC if no timezone info provided
            v = v.replace(tzinfo=timezone.utc)
        return v

    @field_validator("detection_time")
    @classmethod
    def validate_detection_time(cls, v: datetime | None) -> datetime | None:
        """Ensure detection_time is timezone-aware if provided."""
        if v is not None and v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v

    @field_validator("resolution_time")
    @classmethod
    def validate_resolution_time(cls, v: datetime | None) -> datetime | None:
        """Ensure resolution_time is timezone-aware if provided."""
        if v is not None and v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v
