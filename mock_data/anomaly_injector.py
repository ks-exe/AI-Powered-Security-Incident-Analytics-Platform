"""Anomaly pattern injection for mock security event generation.

Generates realistic anomaly patterns that the IsolationForest model should detect:
- Burst attacks: 50+ failed_logins from a single IP within 5 minutes
- Off-hours privilege escalation: privilege_escalation events outside business hours
- Geographic anomalies: events from unusual countries (KP, IR, SY) with higher severity

Requirements: 1.9, 1.10
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from faker import Faker
from numpy.random import Generator

from mock_data.distributions import _generate_external_ips
from mock_data.schemas import EventType, Severity


@dataclass
class AnomalyConfig:
    """Configuration for anomaly pattern injection.

    Attributes:
        burst_count: Number of failed_login events per burst window (50+).
        burst_window_minutes: Duration of each burst window in minutes.
        burst_windows: Number of burst windows to inject (3-5).
        off_hours_escalation_count: Number of privilege_escalation events outside business hours.
        geographic_anomaly_countries: Countries considered anomalous for geographic injection.
    """

    burst_count: int = 50
    burst_window_minutes: int = 5
    burst_windows: int = 4
    off_hours_escalation_count: int = 15
    geographic_anomaly_countries: list[str] = field(
        default_factory=lambda: ["KP", "IR", "SY"]
    )


def inject_anomalies(
    rng: Generator,
    start_time: datetime,
    time_range_days: int,
    anomaly_config: AnomalyConfig | None = None,
) -> list[dict]:
    """Inject anomaly patterns into the event stream.

    Generates anomalous security events that should be detectable by
    the IsolationForest anomaly detection model.

    Args:
        rng: NumPy random Generator instance for reproducibility.
        start_time: Start of the time range for event generation.
        time_range_days: Number of days the time range spans.
        anomaly_config: Configuration for anomaly injection. Defaults to AnomalyConfig().

    Returns:
        List of event dictionaries conforming to SecurityEvent schema fields.
    """
    if anomaly_config is None:
        anomaly_config = AnomalyConfig()

    fake = Faker()
    Faker.seed(int(rng.integers(0, 2**31)))

    events: list[dict] = []

    # Generate burst attack events
    burst_events = _inject_burst_attacks(rng, fake, start_time, time_range_days, anomaly_config)
    events.extend(burst_events)

    # Generate off-hours privilege escalation events
    escalation_events = _inject_off_hours_escalation(
        rng, fake, start_time, time_range_days, anomaly_config
    )
    events.extend(escalation_events)

    # Generate geographic anomaly events
    geo_events = _inject_geographic_anomalies(
        rng, fake, start_time, time_range_days, anomaly_config
    )
    events.extend(geo_events)

    return events

# Realistic values for generated events
_DEPARTMENTS = ["IT", "Finance", "Engineering", "HR", "Marketing", "Sales", "Legal", "Operations"]
_OPERATING_SYSTEMS = ["Windows 11", "Windows 10", "macOS Sonoma", "Ubuntu 22.04", "RHEL 9"]


def _inject_burst_attacks(
    rng: Generator,
    fake: Faker,
    start_time: datetime,
    time_range_days: int,
    anomaly_config: AnomalyConfig,
) -> list[dict]:
    """Inject burst attack anomalies: many failed_logins from a single IP in a short window.

    For each burst window, picks a random time within the date range and a single
    external IP, then generates burst_count failed_login events within
    burst_window_minutes from that IP.

    Args:
        rng: NumPy random Generator for reproducibility.
        fake: Faker instance for realistic usernames/hostnames.
        start_time: Start of the overall time range.
        time_range_days: Duration of the time range in days.
        anomaly_config: Configuration controlling burst parameters.

    Returns:
        List of event dictionaries representing burst attack events.
    """
    events: list[dict] = []
    total_seconds = time_range_days * 24 * 3600
    window_seconds = anomaly_config.burst_window_minutes * 60

    for _ in range(anomaly_config.burst_windows):
        # Pick a random start time for this burst window
        burst_offset = int(rng.integers(0, max(1, total_seconds - window_seconds)))
        burst_start = start_time + timedelta(seconds=burst_offset)

        # Pick a single external IP for this burst
        attacker_ip = _generate_external_ips(rng, 1)[0]

        # Pick severity distribution for burst: high or critical
        severities = [Severity.HIGH.value, Severity.CRITICAL.value]

        for _ in range(anomaly_config.burst_count):
            # Spread events within the burst window
            event_offset_seconds = int(rng.integers(0, window_seconds))
            event_time = burst_start + timedelta(seconds=event_offset_seconds)

            severity = rng.choice(severities)

            # Generate detection and resolution times
            detection_delay_minutes = float(rng.uniform(1, 60))
            detection_time = event_time + timedelta(minutes=detection_delay_minutes)

            resolution_delay_minutes = float(rng.uniform(10, 480))
            resolution_time = detection_time + timedelta(minutes=resolution_delay_minutes)

            event = {
                "event_id": str(uuid4()),
                "event_time": event_time,
                "username": fake.user_name(),
                "src_ip": attacker_ip,
                "destination_ip": None,
                "hostname": fake.hostname(),
                "event_type": EventType.FAILED_LOGIN.value,
                "severity": severity,
                "status": "failure",
                "country": fake.country_code(),
                "operating_system": rng.choice(_OPERATING_SYSTEMS),
                "department": rng.choice(_DEPARTMENTS),
                "detection_time": detection_time,
                "resolution_time": resolution_time,
            }
            events.append(event)

    return events


def _inject_off_hours_escalation(
    rng: Generator,
    fake: Faker,
    start_time: datetime,
    time_range_days: int,
    anomaly_config: AnomalyConfig,
) -> list[dict]:
    """Inject off-hours privilege escalation anomalies.

    Generates privilege_escalation events outside business hours (before 09:00
    or after 17:00 UTC) with higher severity.

    Args:
        rng: NumPy random Generator for reproducibility.
        fake: Faker instance for realistic usernames/hostnames.
        start_time: Start of the overall time range.
        time_range_days: Duration of the time range in days.
        anomaly_config: Configuration controlling escalation count.

    Returns:
        List of event dictionaries representing off-hours privilege escalation events.
    """
    events: list[dict] = []
    severities = [Severity.HIGH.value, Severity.CRITICAL.value]

    for _ in range(anomaly_config.off_hours_escalation_count):
        # Pick a random day
        day_offset = int(rng.integers(0, time_range_days))

        # Generate a time outside business hours (before 09:00 or after 17:00 UTC)
        # Off-hours: [0, 9) and [17, 24) = 16 hours total
        off_hours_seconds = 16 * 3600
        second_in_window = int(rng.integers(0, off_hours_seconds))

        # Map to actual time
        pre_business_seconds = 9 * 3600  # 0:00 to 9:00
        if second_in_window < pre_business_seconds:
            # Falls in [0:00, 9:00)
            event_time = start_time.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=day_offset, seconds=second_in_window)
        else:
            # Falls in [17:00, 24:00)
            offset_from_17 = second_in_window - pre_business_seconds
            event_time = start_time.replace(
                hour=17, minute=0, second=0, microsecond=0
            ) + timedelta(days=day_offset, seconds=offset_from_17)

        severity = rng.choice(severities)

        # Generate detection and resolution times
        detection_delay_minutes = float(rng.uniform(1, 60))
        detection_time = event_time + timedelta(minutes=detection_delay_minutes)

        resolution_delay_minutes = float(rng.uniform(10, 480))
        resolution_time = detection_time + timedelta(minutes=resolution_delay_minutes)

        event = {
            "event_id": str(uuid4()),
            "event_time": event_time,
            "username": fake.user_name(),
            "src_ip": _generate_external_ips(rng, 1)[0],
            "destination_ip": None,
            "hostname": fake.hostname(),
            "event_type": EventType.PRIVILEGE_ESCALATION.value,
            "severity": severity,
            "status": "detected",
            "country": fake.country_code(),
            "operating_system": rng.choice(_OPERATING_SYSTEMS),
            "department": rng.choice(_DEPARTMENTS),
            "detection_time": detection_time,
            "resolution_time": resolution_time,
        }
        events.append(event)

    return events


def _inject_geographic_anomalies(
    rng: Generator,
    fake: Faker,
    start_time: datetime,
    time_range_days: int,
    anomaly_config: AnomalyConfig,
) -> list[dict]:
    """Inject geographic anomaly events from unusual countries.

    Generates ~5 events per anomaly country with a mix of suspicious_ip_activity
    and brute_force_attempt event types, higher severity, and external IPs.

    Args:
        rng: NumPy random Generator for reproducibility.
        fake: Faker instance for realistic usernames/hostnames.
        start_time: Start of the overall time range.
        time_range_days: Duration of the time range in days.
        anomaly_config: Configuration with geographic_anomaly_countries list.

    Returns:
        List of event dictionaries representing geographic anomaly events.
    """
    events: list[dict] = []
    total_seconds = time_range_days * 24 * 3600
    severities = [Severity.HIGH.value, Severity.CRITICAL.value]
    geo_event_types = [EventType.SUSPICIOUS_IP.value, EventType.BRUTE_FORCE.value]
    events_per_country = 5

    for country in anomaly_config.geographic_anomaly_countries:
        for _ in range(events_per_country):
            # Random time within the full range
            event_offset = int(rng.integers(0, total_seconds))
            event_time = start_time + timedelta(seconds=event_offset)

            severity = rng.choice(severities)
            event_type = rng.choice(geo_event_types)

            # Generate detection and resolution times
            detection_delay_minutes = float(rng.uniform(1, 60))
            detection_time = event_time + timedelta(minutes=detection_delay_minutes)

            resolution_delay_minutes = float(rng.uniform(10, 480))
            resolution_time = detection_time + timedelta(minutes=resolution_delay_minutes)

            event = {
                "event_id": str(uuid4()),
                "event_time": event_time,
                "username": fake.user_name(),
                "src_ip": _generate_external_ips(rng, 1)[0],
                "destination_ip": None,
                "hostname": fake.hostname(),
                "event_type": event_type,
                "severity": severity,
                "status": "detected",
                "country": country,
                "operating_system": rng.choice(_OPERATING_SYSTEMS),
                "department": rng.choice(_DEPARTMENTS),
                "detection_time": detection_time,
                "resolution_time": resolution_time,
            }
            events.append(event)

    return events
