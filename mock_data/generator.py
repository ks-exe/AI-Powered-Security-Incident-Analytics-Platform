"""Main generator orchestrator for mock security event generation.

Coordinates all generation modules to produce realistic security log events
with configurable volume, temporal patterns, field correlations, and anomalies.
Supports deterministic output via seed parameter and outputs to JSONL and Parquet formats.

Requirements: 1.1, 1.7, 1.8
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd
import yaml
from faker import Faker
from numpy.random import Generator

from mock_data.anomaly_injector import AnomalyConfig, inject_anomalies
from mock_data.distributions import (
    sample_event_type,
    sample_ip_addresses,
    sample_severity,
    sample_timestamps,
)
from mock_data.schemas import EventType, Severity
from scripts.logging_config import get_logger

logger = get_logger("mock_data_generator")

# Attack event types that get detection_time and resolution_time
ATTACK_EVENT_TYPES = {
    EventType.MALWARE_ALERT.value,
    EventType.PRIVILEGE_ESCALATION.value,
    EventType.SUSPICIOUS_IP.value,
    EventType.BRUTE_FORCE.value,
}

# Departments and their correlation with internal IPs
_INTERNAL_IP_DEPARTMENTS = ["IT", "Engineering", "Operations"]
_ALL_DEPARTMENTS = ["IT", "Finance", "Engineering", "HR", "Marketing", "Sales", "Legal", "Operations"]

# Operating systems
_OPERATING_SYSTEMS = ["Windows 11", "Windows 10", "macOS Sonoma", "Ubuntu 22.04", "RHEL 9"]

# Weighted country distribution favoring common countries
_COUNTRY_WEIGHTS = {
    "US": 0.35,
    "GB": 0.15,
    "DE": 0.12,
    "JP": 0.10,
    "AU": 0.08,
    "CA": 0.06,
    "FR": 0.05,
    "IN": 0.04,
    "BR": 0.03,
    "SG": 0.02,
}

# Status mappings by event type
_STATUS_MAP = {
    EventType.FAILED_LOGIN.value: ["failure"],
    EventType.SUCCESSFUL_LOGIN.value: ["success"],
    EventType.MALWARE_ALERT.value: ["detected", "blocked"],
    EventType.PRIVILEGE_ESCALATION.value: ["detected", "blocked"],
    EventType.SUSPICIOUS_IP.value: ["detected", "blocked"],
    EventType.VPN_LOGIN.value: ["success"],
    EventType.ACCOUNT_LOCKOUT.value: ["failure"],
    EventType.BRUTE_FORCE.value: ["detected", "blocked"],
}

# Higher severity weights for attack events (correlation requirement 1.10)
_ATTACK_SEVERITY_WEIGHTS = {
    Severity.LOW.value: 0.10,
    Severity.MEDIUM.value: 0.20,
    Severity.HIGH.value: 0.40,
    Severity.CRITICAL.value: 0.30,
}


@dataclass
class GeneratorConfig:
    """Configuration for the security event generator.

    Attributes:
        count: Number of events to generate (10,000 to 1,000,000).
        seed: Random seed for deterministic output. None for non-deterministic.
        time_range_days: Number of days the event time range spans.
        output_dir: Directory to write output files.
        output_formats: List of output formats ("jsonl", "parquet").
        severity_weights: Mapping of severity to probability weight.
        event_type_weights: Mapping of event type to probability weight.
        business_hour_ratio: Proportion of events during 09:00-17:00 UTC.
        internal_ip_ratio: Proportion of internal (RFC1918) IP addresses.
        anomaly_config: Configuration for anomaly pattern injection.
    """

    count: int = 10_000
    seed: int | None = None
    time_range_days: int = 30
    output_dir: Path = field(default_factory=lambda: Path("mock_data"))
    output_formats: list[str] = field(default_factory=lambda: ["jsonl", "parquet"])
    severity_weights: dict[str, float] = field(
        default_factory=lambda: {
            "low": 0.40,
            "medium": 0.30,
            "high": 0.20,
            "critical": 0.10,
        }
    )
    event_type_weights: dict[str, float] = field(default_factory=dict)
    business_hour_ratio: float = 0.70
    internal_ip_ratio: float = 0.60
    anomaly_config: AnomalyConfig = field(default_factory=AnomalyConfig)


def generate_security_events(config: GeneratorConfig) -> list[dict]:
    """Generate security events according to configuration.

    Produces a list of event dictionaries conforming to the SecurityEvent schema.
    Deterministic when config.seed is set. Includes field correlations per
    Requirement 1.10 and anomaly injection per Requirement 1.9.

    Args:
        config: GeneratorConfig controlling generation parameters.

    Returns:
        List of event dictionaries with all SecurityEvent fields populated.
    """
    rng = np.random.default_rng(config.seed)

    # Seed faker from the numpy rng for deterministic fake data
    faker_seed = int(rng.integers(0, 2**31))
    fake = Faker()
    Faker.seed(faker_seed)

    logger.info(
        "Starting event generation",
        extra={"context": {"count": config.count, "seed": config.seed}},
    )

    start_time = datetime.now(timezone.utc) - timedelta(days=config.time_range_days)

    # Sample base distributions
    event_types = sample_event_type(
        rng, n=config.count, weights=config.event_type_weights or None
    )
    timestamps = sample_timestamps(
        rng,
        n=config.count,
        start_time=start_time,
        time_range_days=config.time_range_days,
        business_hour_ratio=config.business_hour_ratio,
    )
    ip_addresses = sample_ip_addresses(
        rng, n=config.count, internal_ratio=config.internal_ip_ratio
    )

    # Generate events
    events: list[dict] = []
    brute_force_events_for_lockout: list[dict] = []

    for i in range(config.count):
        event_type = event_types[i]
        event_time = timestamps[i]
        src_ip = ip_addresses[i]

        # Determine if IP is internal (RFC1918 check)
        is_internal = _is_rfc1918(src_ip)

        # Correlate department with internal IP (Requirement 1.10)
        if is_internal:
            department = str(rng.choice(_INTERNAL_IP_DEPARTMENTS))
        else:
            department = str(rng.choice(_ALL_DEPARTMENTS))

        # Correlate severity with attack events (Requirement 1.10)
        if event_type in ATTACK_EVENT_TYPES:
            severity = sample_severity(rng, n=1, weights=_ATTACK_SEVERITY_WEIGHTS)[0]
        else:
            severity = sample_severity(rng, n=1, weights=config.severity_weights)[0]

        # Generate status based on event type
        status_options = _STATUS_MAP.get(event_type, ["success"])
        status = str(rng.choice(status_options))

        # Generate detection_time and resolution_time for attack events
        detection_time = None
        resolution_time = None
        if event_type in ATTACK_EVENT_TYPES:
            detection_delay_minutes = float(rng.uniform(1, 60))
            detection_time = event_time + timedelta(minutes=detection_delay_minutes)
            resolution_delay_minutes = float(rng.uniform(10, 480))
            resolution_time = detection_time + timedelta(minutes=resolution_delay_minutes)

        # Generate destination IP for some events
        destination_ip = None
        if event_type in (EventType.SUSPICIOUS_IP.value, EventType.MALWARE_ALERT.value):
            destination_ip = sample_ip_addresses(rng, n=1, internal_ratio=0.8)[0]

        # Generate hostname with department pattern
        hostname = _generate_hostname(rng, fake, department)

        # Generate country
        country = _sample_country(rng)

        # Generate OS
        operating_system = str(rng.choice(_OPERATING_SYSTEMS))

        event = {
            "event_id": str(uuid4()),
            "event_time": event_time,
            "username": fake.user_name(),
            "src_ip": src_ip,
            "destination_ip": destination_ip,
            "hostname": hostname,
            "event_type": event_type,
            "severity": severity,
            "status": status,
            "country": country,
            "operating_system": operating_system,
            "department": department,
            "detection_time": detection_time,
            "resolution_time": resolution_time,
        }
        events.append(event)

        # Track brute_force events for correlated account_lockout (Requirement 1.10)
        if event_type == EventType.BRUTE_FORCE.value:
            brute_force_events_for_lockout.append(event)

    # Generate correlated account_lockout events for some brute_force events
    lockout_events = _generate_correlated_lockouts(rng, fake, brute_force_events_for_lockout)
    events.extend(lockout_events)

    # Inject anomaly events
    anomaly_events = inject_anomalies(
        rng, start_time, config.time_range_days, config.anomaly_config
    )
    events.extend(anomaly_events)

    logger.info(
        "Event generation complete",
        extra={
            "context": {
                "total_events": len(events),
                "base_events": config.count,
                "lockout_events": len(lockout_events),
                "anomaly_events": len(anomaly_events),
            }
        },
    )

    return events


def write_events(events: list[dict], config: GeneratorConfig) -> dict[str, Path]:
    """Write events to configured output formats (JSONL and/or Parquet).

    Args:
        events: List of event dictionaries to write.
        config: GeneratorConfig with output_dir and output_formats.

    Returns:
        Mapping of format name to output file path.
    """
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    output_paths: dict[str, Path] = {}

    if "jsonl" in config.output_formats:
        jsonl_path = output_dir / "security_events.jsonl"
        _write_jsonl(events, jsonl_path)
        output_paths["jsonl"] = jsonl_path
        logger.info(
            "Wrote JSONL output",
            extra={"context": {"path": str(jsonl_path), "records": len(events)}},
        )

    if "parquet" in config.output_formats:
        parquet_path = output_dir / "security_events.parquet"
        _write_parquet(events, parquet_path)
        output_paths["parquet"] = parquet_path
        logger.info(
            "Wrote Parquet output",
            extra={"context": {"path": str(parquet_path), "records": len(events)}},
        )

    return output_paths


def load_config(config_path: Path | None = None) -> GeneratorConfig:
    """Load generator configuration from a YAML file.

    Args:
        config_path: Path to the YAML config file. Defaults to mock_data/config.yaml.

    Returns:
        GeneratorConfig populated from the YAML file values.
    """
    if config_path is None:
        config_path = Path("mock_data/config.yaml")

    if not config_path.exists():
        logger.info("No config file found, using defaults")
        return GeneratorConfig()

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    if not raw:
        return GeneratorConfig()

    # Build anomaly config if present
    anomaly_raw = raw.get("anomaly_config", {})
    anomaly_config = AnomalyConfig(
        burst_count=anomaly_raw.get("burst_count", 50),
        burst_window_minutes=anomaly_raw.get("burst_window_minutes", 5),
        burst_windows=anomaly_raw.get("burst_windows", 4),
        off_hours_escalation_count=anomaly_raw.get("off_hours_escalation_count", 15),
        geographic_anomaly_countries=anomaly_raw.get(
            "geographic_anomaly_countries", ["KP", "IR", "SY"]
        ),
    )

    default_severity = {"low": 0.40, "medium": 0.30, "high": 0.20, "critical": 0.10}

    return GeneratorConfig(
        count=raw.get("count", 10_000),
        seed=raw.get("seed"),
        time_range_days=raw.get("time_range_days", 30),
        output_dir=Path(raw.get("output_dir", "mock_data")),
        output_formats=raw.get("output_formats", ["jsonl", "parquet"]),
        severity_weights=raw.get("severity_weights", default_severity),
        event_type_weights=raw.get("event_type_weights", {}),
        business_hour_ratio=raw.get("business_hour_ratio", 0.70),
        internal_ip_ratio=raw.get("internal_ip_ratio", 0.60),
        anomaly_config=anomaly_config,
    )


# --- Private helpers ---


def _is_rfc1918(ip: str) -> bool:
    """Check if an IP address is in RFC1918 private ranges."""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    first, second = int(parts[0]), int(parts[1])
    if first == 10:
        return True
    if first == 172 and 16 <= second <= 31:
        return True
    if first == 192 and second == 168:
        return True
    return False


def _generate_hostname(rng: Generator, fake: Faker, department: str) -> str:
    """Generate a hostname with department prefix pattern.

    Format: WS-{DEPT_ABBREV}-{NNN}
    """
    dept_abbrev = department[:3].upper()
    number = int(rng.integers(1, 999))
    return f"WS-{dept_abbrev}-{number:03d}"


def _sample_country(rng: Generator) -> str:
    """Sample a country code from weighted distribution."""
    countries = list(_COUNTRY_WEIGHTS.keys())
    probabilities = np.array(list(_COUNTRY_WEIGHTS.values()), dtype=np.float64)
    probabilities = probabilities / probabilities.sum()
    idx = int(rng.choice(len(countries), p=probabilities))
    return countries[idx]


def _generate_correlated_lockouts(
    rng: Generator,
    fake: Faker,
    brute_force_events: list[dict],
) -> list[dict]:
    """Generate correlated account_lockout events for brute_force attempts.

    Approximately 30% of brute_force_attempt events generate a correlated
    account_lockout event shortly after (Requirement 1.10).

    Args:
        rng: NumPy random Generator for reproducibility.
        fake: Faker instance for realistic data.
        brute_force_events: List of brute_force_attempt event dicts.

    Returns:
        List of account_lockout event dictionaries.
    """
    lockout_events: list[dict] = []
    lockout_probability = 0.30

    for bf_event in brute_force_events:
        if rng.random() < lockout_probability:
            # Lockout occurs 1-5 minutes after brute force attempt
            delay_seconds = int(rng.integers(60, 300))
            lockout_time = bf_event["event_time"] + timedelta(seconds=delay_seconds)

            lockout_event = {
                "event_id": str(uuid4()),
                "event_time": lockout_time,
                "username": bf_event["username"],
                "src_ip": bf_event["src_ip"],
                "destination_ip": None,
                "hostname": bf_event["hostname"],
                "event_type": EventType.ACCOUNT_LOCKOUT.value,
                "severity": "medium",
                "status": "failure",
                "country": bf_event["country"],
                "operating_system": bf_event["operating_system"],
                "department": bf_event["department"],
                "detection_time": None,
                "resolution_time": None,
            }
            lockout_events.append(lockout_event)

    return lockout_events


def _write_jsonl(events: list[dict], path: Path) -> None:
    """Write events to JSONL format with ISO8601 datetime serialization."""
    with open(path, "w", encoding="utf-8") as f:
        for event in events:
            serialized = _serialize_event(event)
            f.write(json.dumps(serialized, default=str) + "\n")


def _serialize_event(event: dict) -> dict:
    """Serialize an event dict with datetime fields to ISO8601 strings."""
    serialized = {}
    for key, value in event.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


def _write_parquet(events: list[dict], path: Path) -> None:
    """Write events to Parquet format via pandas DataFrame."""
    df = pd.DataFrame(events)
    df.to_parquet(path, index=False, engine="pyarrow")


# --- CLI entry point ---


def main() -> None:
    """Main entry point for running the generator from the command line."""
    config = load_config()
    logger.info(
        "Mock Data Generator started",
        extra={"context": {"config_count": config.count, "seed": config.seed}},
    )

    events = generate_security_events(config)
    output_paths = write_events(events, config)

    logger.info(
        "Mock Data Generator finished",
        extra={
            "context": {
                "total_events": len(events),
                "output_files": {fmt: str(p) for fmt, p in output_paths.items()},
            }
        },
    )


if __name__ == "__main__":
    main()
