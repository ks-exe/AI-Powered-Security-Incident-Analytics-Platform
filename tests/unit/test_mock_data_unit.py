"""Unit tests for Mock Data Generator.

Tests schema validation, severity distribution, business-hour clustering,
anomaly injection patterns, field correlations, and IP address generation.

Requirements: 1.4, 1.5, 1.9, 1.10
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone

import numpy as np
import pytest
from pydantic import ValidationError

from mock_data.anomaly_injector import AnomalyConfig, inject_anomalies
from mock_data.distributions import (
    DEFAULT_SEVERITY_WEIGHTS,
    sample_ip_addresses,
    sample_severity,
    sample_timestamps,
)
from mock_data.generator import (
    ATTACK_EVENT_TYPES,
    GeneratorConfig,
    _is_rfc1918,
    generate_security_events,
)
from mock_data.schemas import EventType, SecurityEvent, Severity

# Fixed seed for deterministic tests
SEED = 42


# --- 1. Schema Validation ---


@pytest.mark.unit
class TestSchemaValidation:
    """Test SecurityEvent schema validation with known inputs."""

    def test_valid_event_passes_validation(self):
        """A SecurityEvent with all valid fields should pass validation."""
        event = SecurityEvent(
            event_id="a1b2c3d4-e5f6-4890-abcd-ef1234567890",
            event_time=datetime(2024, 1, 15, 14, 32, 7, tzinfo=timezone.utc),
            username="john.smith",
            src_ip="192.168.1.105",
            destination_ip="10.0.0.50",
            hostname="WS-FIN-042",
            event_type=EventType.FAILED_LOGIN,
            severity=Severity.HIGH,
            status="failure",
            country="US",
            operating_system="Windows 11",
            department="Finance",
            detection_time=datetime(2024, 1, 15, 14, 35, 22, tzinfo=timezone.utc),
            resolution_time=datetime(2024, 1, 15, 15, 10, 45, tzinfo=timezone.utc),
        )
        assert event.event_id == "a1b2c3d4-e5f6-4890-abcd-ef1234567890"
        assert event.src_ip == "192.168.1.105"
        assert event.severity == Severity.HIGH

    def test_invalid_uuid_raises_validation_error(self):
        """An event_id that is not a valid UUID v4 should raise ValidationError."""
        with pytest.raises(ValidationError, match="event_id"):
            SecurityEvent(
                event_id="not-a-valid-uuid",
                event_time=datetime(2024, 1, 15, 14, 32, 7, tzinfo=timezone.utc),
                username="john.smith",
                src_ip="192.168.1.105",
                hostname="WS-FIN-042",
                event_type=EventType.FAILED_LOGIN,
                severity=Severity.HIGH,
                status="failure",
                country="US",
                operating_system="Windows 11",
                department="Finance",
            )

    def test_invalid_ip_raises_validation_error(self):
        """An src_ip that is not a valid IPv4 address should raise ValidationError."""
        with pytest.raises(ValidationError, match="src_ip"):
            SecurityEvent(
                event_id="a1b2c3d4-e5f6-4890-abcd-ef1234567890",
                event_time=datetime(2024, 1, 15, 14, 32, 7, tzinfo=timezone.utc),
                username="john.smith",
                src_ip="999.999.999.999",
                hostname="WS-FIN-042",
                event_type=EventType.FAILED_LOGIN,
                severity=Severity.HIGH,
                status="failure",
                country="US",
                operating_system="Windows 11",
                department="Finance",
            )

    def test_invalid_destination_ip_raises_validation_error(self):
        """An invalid destination_ip should raise ValidationError."""
        with pytest.raises(ValidationError, match="destination_ip"):
            SecurityEvent(
                event_id="a1b2c3d4-e5f6-4890-abcd-ef1234567890",
                event_time=datetime(2024, 1, 15, 14, 32, 7, tzinfo=timezone.utc),
                username="john.smith",
                src_ip="192.168.1.105",
                destination_ip="not.an.ip.addr",
                hostname="WS-FIN-042",
                event_type=EventType.FAILED_LOGIN,
                severity=Severity.HIGH,
                status="failure",
                country="US",
                operating_system="Windows 11",
                department="Finance",
            )

    def test_uuid_v4_format_enforced(self):
        """UUID must be version 4 (4th group starts with 4)."""
        # Valid UUID but version 1 (not v4) — 3rd group starts with 1
        with pytest.raises(ValidationError, match="event_id"):
            SecurityEvent(
                event_id="a1b2c3d4-e5f6-1890-abcd-ef1234567890",
                event_time=datetime(2024, 1, 15, 14, 32, 7, tzinfo=timezone.utc),
                username="john.smith",
                src_ip="192.168.1.105",
                hostname="WS-FIN-042",
                event_type=EventType.FAILED_LOGIN,
                severity=Severity.HIGH,
                status="failure",
                country="US",
                operating_system="Windows 11",
                department="Finance",
            )


# --- 2. Severity Distribution ---


@pytest.mark.unit
class TestSeverityDistribution:
    """Test severity distribution matches configured weights within statistical tolerance."""

    def test_default_severity_distribution(self):
        """Generate 10,000 events with default weights.

        Low ~40% ± 5%, medium ~30% ± 5%, high ~20% ± 5%, critical ~10% ± 5%.
        """
        rng = np.random.default_rng(SEED)
        n = 10_000
        severities = sample_severity(rng, n=n, weights=DEFAULT_SEVERITY_WEIGHTS)

        counts = Counter(severities)
        total = len(severities)

        expected = {"low": 0.40, "medium": 0.30, "high": 0.20, "critical": 0.10}
        tolerance = 0.05

        for severity, expected_weight in expected.items():
            actual_ratio = counts.get(severity, 0) / total
            assert abs(actual_ratio - expected_weight) < tolerance, (
                f"Severity '{severity}': expected ~{expected_weight:.2f}, "
                f"got {actual_ratio:.3f} (tolerance: ±{tolerance})"
            )

    def test_all_severity_levels_present(self):
        """All four severity levels should appear in a large enough sample."""
        rng = np.random.default_rng(SEED)
        severities = sample_severity(rng, n=10_000, weights=DEFAULT_SEVERITY_WEIGHTS)
        unique_severities = set(severities)
        assert unique_severities == {"low", "medium", "high", "critical"}


# --- 3. Business-Hour Clustering ---


@pytest.mark.unit
class TestBusinessHourClustering:
    """Test that business_hour_ratio=0.70 produces ~70% timestamps in 09:00-17:00 UTC."""

    def test_business_hour_ratio_70_percent(self):
        """Generate events with business_hour_ratio=0.70.

        Approximately 70% (±10% tolerance) should fall in 09:00-17:00 UTC.
        """
        rng = np.random.default_rng(SEED)
        n = 10_000
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)

        timestamps = sample_timestamps(
            rng,
            n=n,
            start_time=start_time,
            time_range_days=30,
            business_hour_ratio=0.70,
        )

        business_hour_count = sum(1 for ts in timestamps if 9 <= ts.hour < 17)
        actual_ratio = business_hour_count / n
        tolerance = 0.10

        assert abs(actual_ratio - 0.70) < tolerance, (
            f"Business hour ratio: expected ~0.70, got {actual_ratio:.3f} "
            f"(tolerance: ±{tolerance})"
        )

    def test_off_hours_events_exist(self):
        """Some events should fall outside business hours."""
        rng = np.random.default_rng(SEED)
        n = 1_000
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)

        timestamps = sample_timestamps(
            rng,
            n=n,
            start_time=start_time,
            time_range_days=30,
            business_hour_ratio=0.70,
        )

        off_hours_count = sum(1 for ts in timestamps if ts.hour < 9 or ts.hour >= 17)
        assert off_hours_count > 0, "Should have some off-hours events"
        # ~30% should be off-hours
        off_ratio = off_hours_count / n
        assert off_ratio > 0.15, f"Off-hours ratio too low: {off_ratio:.3f}"


# --- 4. Anomaly Injection ---


@pytest.mark.unit
class TestAnomalyInjection:
    """Test anomaly injection produces expected burst patterns with default config."""

    def test_default_config_burst_events_count(self):
        """Default config: 50 * 4 = 200 failed_login burst events."""
        rng = np.random.default_rng(SEED)
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        config = AnomalyConfig()  # defaults: burst_count=50, burst_windows=4

        events = inject_anomalies(rng, start_time, 30, config)

        burst_events = [
            e for e in events if e["event_type"] == EventType.FAILED_LOGIN.value
        ]
        expected = config.burst_count * config.burst_windows  # 50 * 4 = 200
        assert len(burst_events) == expected, (
            f"Expected {expected} burst events, got {len(burst_events)}"
        )

    def test_default_config_off_hours_escalation_count(self):
        """Default config: 15 off-hours privilege escalation events."""
        rng = np.random.default_rng(SEED)
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        config = AnomalyConfig()  # default off_hours_escalation_count=15

        events = inject_anomalies(rng, start_time, 30, config)

        escalation_events = [
            e for e in events
            if e["event_type"] == EventType.PRIVILEGE_ESCALATION.value
        ]
        assert len(escalation_events) == 15, (
            f"Expected 15 escalation events, got {len(escalation_events)}"
        )

    def test_default_config_geographic_anomaly_count(self):
        """Default config: 5 per country × 3 countries = 15 geographic anomaly events."""
        rng = np.random.default_rng(SEED)
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        config = AnomalyConfig()  # default countries: KP, IR, SY

        events = inject_anomalies(rng, start_time, 30, config)

        geo_event_types = {EventType.SUSPICIOUS_IP.value, EventType.BRUTE_FORCE.value}
        geo_events = [
            e for e in events
            if e["country"] in config.geographic_anomaly_countries
            and e["event_type"] in geo_event_types
        ]

        # Exactly 5 per country = 15 total
        expected = 5 * len(config.geographic_anomaly_countries)  # 5 * 3 = 15
        assert len(geo_events) >= expected, (
            f"Expected at least {expected} geographic anomaly events, got {len(geo_events)}"
        )

    def test_burst_events_same_ip_per_window(self):
        """Each burst window should have all events from a single IP."""
        rng = np.random.default_rng(SEED)
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        config = AnomalyConfig()

        events = inject_anomalies(rng, start_time, 30, config)

        burst_events = [
            e for e in events if e["event_type"] == EventType.FAILED_LOGIN.value
        ]

        # Group by src_ip
        ip_groups = Counter(e["src_ip"] for e in burst_events)

        # Each burst window uses a single IP → burst_windows distinct IPs
        assert len(ip_groups) == config.burst_windows, (
            f"Expected {config.burst_windows} distinct burst IPs, got {len(ip_groups)}"
        )

        # Each IP should have exactly burst_count events
        for ip, count in ip_groups.items():
            assert count == config.burst_count, (
                f"IP {ip} has {count} events, expected {config.burst_count}"
            )

    def test_burst_events_within_time_window(self):
        """All events in a single burst should span at most burst_window_minutes."""
        rng = np.random.default_rng(SEED)
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        config = AnomalyConfig()

        events = inject_anomalies(rng, start_time, 30, config)

        burst_events = [
            e for e in events if e["event_type"] == EventType.FAILED_LOGIN.value
        ]

        # Group events by IP (each IP = one burst window)
        ip_events: dict[str, list[datetime]] = defaultdict(list)
        for e in burst_events:
            ip_events[e["src_ip"]].append(e["event_time"])

        max_window_seconds = config.burst_window_minutes * 60

        for ip, times in ip_events.items():
            time_span = (max(times) - min(times)).total_seconds()
            assert time_span <= max_window_seconds, (
                f"Burst from IP {ip} spans {time_span}s, "
                f"max allowed is {max_window_seconds}s"
            )

    def test_off_hours_escalation_outside_business_hours(self):
        """All off-hours escalation events should be before 09:00 or after 17:00 UTC."""
        rng = np.random.default_rng(SEED)
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        config = AnomalyConfig()

        events = inject_anomalies(rng, start_time, 30, config)

        escalation_events = [
            e for e in events
            if e["event_type"] == EventType.PRIVILEGE_ESCALATION.value
        ]

        for event in escalation_events:
            hour = event["event_time"].hour
            assert hour < 9 or hour >= 17, (
                f"Off-hours escalation at hour {hour} is within business hours"
            )


# --- 5. Field Correlations ---


@pytest.mark.unit
class TestFieldCorrelations:
    """Test field correlations: internal IPs ↔ departments, attacks ↔ higher severity."""

    @pytest.fixture
    def seeded_events(self):
        """Generate events with fixed seed for deterministic correlation testing."""
        config = GeneratorConfig(count=5_000, seed=SEED, time_range_days=30)
        return generate_security_events(config)

    def test_internal_ips_correlate_with_tech_departments(self, seeded_events):
        """Internal IPs should correlate with IT/Engineering/Operations more than external IPs."""
        internal_departments = {"IT", "Engineering", "Operations"}

        internal_events = [e for e in seeded_events if _is_rfc1918(e["src_ip"])]
        external_events = [e for e in seeded_events if not _is_rfc1918(e["src_ip"])]

        assert len(internal_events) > 0
        assert len(external_events) > 0

        internal_dept_ratio_internal_ip = sum(
            1 for e in internal_events if e["department"] in internal_departments
        ) / len(internal_events)

        internal_dept_ratio_external_ip = sum(
            1 for e in external_events if e["department"] in internal_departments
        ) / len(external_events)

        # Internal IPs should have a significantly higher ratio of tech departments
        assert internal_dept_ratio_internal_ip > internal_dept_ratio_external_ip, (
            f"Internal IP tech-dept ratio ({internal_dept_ratio_internal_ip:.3f}) "
            f"should exceed external IP tech-dept ratio ({internal_dept_ratio_external_ip:.3f})"
        )

    def test_attack_events_have_higher_severity_rank(self, seeded_events):
        """Attack events should have a higher average severity_rank than non-attack events."""
        severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}

        attack_events = [e for e in seeded_events if e["event_type"] in ATTACK_EVENT_TYPES]
        non_attack_events = [
            e for e in seeded_events if e["event_type"] not in ATTACK_EVENT_TYPES
        ]

        assert len(attack_events) > 0
        assert len(non_attack_events) > 0

        avg_attack_severity = sum(
            severity_rank[e["severity"]] for e in attack_events
        ) / len(attack_events)

        avg_non_attack_severity = sum(
            severity_rank[e["severity"]] for e in non_attack_events
        ) / len(non_attack_events)

        assert avg_attack_severity > avg_non_attack_severity, (
            f"Attack avg severity rank ({avg_attack_severity:.2f}) should exceed "
            f"non-attack avg severity rank ({avg_non_attack_severity:.2f})"
        )


# --- 6. IP Address Generation ---


@pytest.mark.unit
class TestIPAddressGeneration:
    """Test IP address generation with configurable internal/external ratio."""

    def test_internal_ratio_60_percent(self):
        """Generate IPs with internal_ratio=0.60, verify ~60% are RFC1918."""
        rng = np.random.default_rng(SEED)
        n = 10_000
        ips = sample_ip_addresses(rng, n=n, internal_ratio=0.60)

        internal_count = sum(1 for ip in ips if _is_rfc1918(ip))
        actual_ratio = internal_count / n
        tolerance = 0.05

        assert abs(actual_ratio - 0.60) < tolerance, (
            f"Internal IP ratio: expected ~0.60, got {actual_ratio:.3f} "
            f"(tolerance: ±{tolerance})"
        )

    def test_all_generated_ips_are_valid_ipv4(self):
        """All generated IPs should be valid IPv4 addresses."""
        import ipaddress

        rng = np.random.default_rng(SEED)
        ips = sample_ip_addresses(rng, n=1_000, internal_ratio=0.60)

        for ip in ips:
            try:
                ipaddress.IPv4Address(ip)
            except ipaddress.AddressValueError:
                pytest.fail(f"Generated invalid IP address: {ip}")

    def test_internal_ips_are_rfc1918(self):
        """IPs generated as internal should be in RFC1918 ranges."""
        rng = np.random.default_rng(SEED)
        # Generate 100% internal
        ips = sample_ip_addresses(rng, n=100, internal_ratio=1.0)

        for ip in ips:
            assert _is_rfc1918(ip), f"IP {ip} should be RFC1918 but isn't"

    def test_external_ips_are_not_rfc1918(self):
        """IPs generated as external should not be in RFC1918 ranges."""
        rng = np.random.default_rng(SEED)
        # Generate 100% external
        ips = sample_ip_addresses(rng, n=100, internal_ratio=0.0)

        for ip in ips:
            assert not _is_rfc1918(ip), f"IP {ip} should be external but is RFC1918"
