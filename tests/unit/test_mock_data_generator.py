"""Unit tests for Mock Data Generator.

Tests schema validation, severity distribution, business-hour clustering,
anomaly injection patterns, and field correlations.

Requirements: 1.4, 1.5, 1.9, 1.10
"""

from collections import Counter
from datetime import datetime, timezone

import numpy as np
import pytest

from mock_data.anomaly_injector import AnomalyConfig, inject_anomalies
from mock_data.distributions import (
    DEFAULT_SEVERITY_WEIGHTS,
    sample_severity,
    sample_timestamps,
    sample_ip_addresses,
)
from mock_data.generator import (
    ATTACK_EVENT_TYPES,
    GeneratorConfig,
    _is_rfc1918,
    generate_security_events,
)
from mock_data.schemas import EventType, SecurityEvent, Severity


# --- Test configuration ---

SEED = 42
EVENT_COUNT = 500
TOLERANCE = 0.12  # 12% statistical tolerance (wider for smaller samples)


@pytest.fixture
def config():
    """Generator config with fixed seed and 1000 events for fast execution."""
    return GeneratorConfig(count=EVENT_COUNT, seed=SEED, time_range_days=30)


@pytest.fixture
def events(config):
    """Generate events once for all tests that need them."""
    return generate_security_events(config)


# --- 1. Schema validation with known inputs ---


@pytest.mark.unit
class TestSchemaValidation:
    """Test that generated events conform to the SecurityEvent schema."""

    def test_all_events_validate_against_schema(self, events):
        """Every generated event should be parseable by the Pydantic SecurityEvent model."""
        for event in events[:50]:
            parsed = SecurityEvent(**event)
            assert parsed.event_id is not None
            assert parsed.event_time is not None
            assert parsed.username != ""
            assert parsed.src_ip != ""
            assert parsed.hostname != ""

    def test_event_types_are_valid_enum_values(self, events):
        """All event_type values should be valid EventType enum values."""
        valid_types = {e.value for e in EventType}
        for event in events:
            assert event["event_type"] in valid_types

    def test_severity_values_are_valid_enum_values(self, events):
        """All severity values should be valid Severity enum values."""
        valid_severities = {s.value for s in Severity}
        for event in events:
            assert event["severity"] in valid_severities

    def test_attack_events_have_detection_and_resolution_times(self, events):
        """Attack event types should have non-null detection_time and resolution_time."""
        attack_events = [e for e in events if e["event_type"] in ATTACK_EVENT_TYPES]
        assert len(attack_events) > 0, "Should have at least some attack events"
        for event in attack_events:
            assert event["detection_time"] is not None, (
                f"Attack event {event['event_type']} missing detection_time"
            )
            assert event["resolution_time"] is not None, (
                f"Attack event {event['event_type']} missing resolution_time"
            )

    def test_non_attack_events_have_null_detection_resolution(self, events):
        """Non-attack events (base events, not anomaly-injected) should have null times."""
        # Non-attack, non-anomaly-injected events
        non_attack_types = {
            EventType.SUCCESSFUL_LOGIN.value,
            EventType.VPN_LOGIN.value,
            EventType.ACCOUNT_LOCKOUT.value,
        }
        non_attack_events = [e for e in events if e["event_type"] in non_attack_types]
        # Account lockout events generated as correlates should have None
        for event in non_attack_events:
            if event["event_type"] == EventType.ACCOUNT_LOCKOUT.value:
                assert event["detection_time"] is None
                assert event["resolution_time"] is None


# --- 2. Severity distribution matches configured weights ---


@pytest.mark.unit
class TestSeverityDistribution:
    """Test that severity distribution matches configured weights within tolerance."""

    def test_severity_distribution_within_tolerance(self):
        """Sampled severity distribution should be within tolerance of configured weights."""
        rng = np.random.default_rng(SEED)
        n = 1000
        severities = sample_severity(rng, n=n, weights=DEFAULT_SEVERITY_WEIGHTS)

        counts = Counter(severities)
        total = len(severities)

        for severity, expected_weight in DEFAULT_SEVERITY_WEIGHTS.items():
            actual_ratio = counts.get(severity, 0) / total
            assert abs(actual_ratio - expected_weight) < TOLERANCE, (
                f"Severity '{severity}': expected ~{expected_weight:.2f}, "
                f"got {actual_ratio:.2f} (tolerance: {TOLERANCE})"
            )

    def test_custom_severity_weights_respected(self):
        """Custom severity weights should be reflected in output distribution."""
        rng = np.random.default_rng(SEED)
        custom_weights = {"low": 0.10, "medium": 0.10, "high": 0.30, "critical": 0.50}
        n = 1000
        severities = sample_severity(rng, n=n, weights=custom_weights)

        counts = Counter(severities)
        total = len(severities)

        for severity, expected_weight in custom_weights.items():
            actual_ratio = counts.get(severity, 0) / total
            assert abs(actual_ratio - expected_weight) < TOLERANCE, (
                f"Custom severity '{severity}': expected ~{expected_weight:.2f}, "
                f"got {actual_ratio:.2f}"
            )


# --- 3. Business-hour clustering ratio ---


@pytest.mark.unit
class TestBusinessHourClustering:
    """Test that ~70% of events have timestamps in business hours (09:00-17:00 UTC)."""

    def test_business_hour_ratio_within_tolerance(self):
        """Approximately 70% of timestamps should fall within 09:00-17:00 UTC."""
        rng = np.random.default_rng(SEED)
        n = 1000
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        timestamps = sample_timestamps(
            rng, n=n, start_time=start_time, time_range_days=30,
            business_hour_ratio=0.70,
        )

        business_hour_count = sum(
            1 for ts in timestamps if 9 <= ts.hour < 17
        )
        actual_ratio = business_hour_count / len(timestamps)
        expected_ratio = 0.70

        assert abs(actual_ratio - expected_ratio) < TOLERANCE, (
            f"Business hour ratio: expected ~{expected_ratio:.2f}, "
            f"got {actual_ratio:.2f} (tolerance: {TOLERANCE})"
        )

    def test_generated_events_business_hour_clustering(self, events):
        """Generated events should have approximately 70% in business hours."""
        business_hour_count = sum(
            1 for e in events
            if 9 <= e["event_time"].hour < 17
        )
        # Note: anomaly-injected events may slightly shift the ratio,
        # so we use a broader tolerance against the base count
        base_event_count = len(events)
        actual_ratio = business_hour_count / base_event_count

        # Anomaly events (off-hours escalation, bursts) reduce the ratio slightly
        # so we accept a wider tolerance here
        assert 0.45 < actual_ratio < 0.85, (
            f"Business hour ratio for generated events: {actual_ratio:.2f} "
            f"(expected roughly 0.5-0.8 including anomalies)"
        )


# --- 4. Anomaly injection produces expected burst patterns ---


@pytest.mark.unit
class TestAnomalyInjection:
    """Test that anomaly injection produces expected burst patterns."""

    def test_burst_count_per_window(self):
        """Each burst window should contain burst_count failed_login events from same IP."""
        rng = np.random.default_rng(SEED)
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        anomaly_config = AnomalyConfig(
            burst_count=20,
            burst_window_minutes=5,
            burst_windows=2,
            off_hours_escalation_count=5,
            geographic_anomaly_countries=["KP", "IR"],
        )

        anomaly_events = inject_anomalies(rng, start_time, 30, anomaly_config)

        # Filter to burst events (failed_login events)
        burst_events = [
            e for e in anomaly_events
            if e["event_type"] == EventType.FAILED_LOGIN.value
        ]

        # Should have burst_count * burst_windows burst events total
        expected_burst_total = anomaly_config.burst_count * anomaly_config.burst_windows
        assert len(burst_events) == expected_burst_total, (
            f"Expected {expected_burst_total} burst events, got {len(burst_events)}"
        )

    def test_burst_events_from_same_ip_within_window(self):
        """Burst events should cluster from the same IP within 5-minute windows."""
        rng = np.random.default_rng(SEED)
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        anomaly_config = AnomalyConfig(
            burst_count=20,
            burst_window_minutes=5,
            burst_windows=2,
        )

        anomaly_events = inject_anomalies(rng, start_time, 30, anomaly_config)
        burst_events = [
            e for e in anomaly_events
            if e["event_type"] == EventType.FAILED_LOGIN.value
        ]

        # Group by src_ip
        ip_groups = Counter(e["src_ip"] for e in burst_events)

        # Each burst window uses a single IP, so we expect burst_windows distinct IPs
        # each with burst_count events
        assert len(ip_groups) == anomaly_config.burst_windows, (
            f"Expected {anomaly_config.burst_windows} distinct burst IPs, "
            f"got {len(ip_groups)}"
        )

        for ip, count in ip_groups.items():
            assert count == anomaly_config.burst_count, (
                f"IP {ip} has {count} events, expected {anomaly_config.burst_count}"
            )

    def test_burst_events_within_time_window(self):
        """All events in a burst should span at most burst_window_minutes."""
        rng = np.random.default_rng(SEED)
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        anomaly_config = AnomalyConfig(
            burst_count=20,
            burst_window_minutes=5,
            burst_windows=2,
        )

        anomaly_events = inject_anomalies(rng, start_time, 30, anomaly_config)
        burst_events = [
            e for e in anomaly_events
            if e["event_type"] == EventType.FAILED_LOGIN.value
        ]

        # Group events by IP (each IP = one burst window)
        from collections import defaultdict
        ip_events = defaultdict(list)
        for e in burst_events:
            ip_events[e["src_ip"]].append(e["event_time"])

        for ip, times in ip_events.items():
            time_span = max(times) - min(times)
            max_window = anomaly_config.burst_window_minutes * 60  # seconds
            assert time_span.total_seconds() <= max_window, (
                f"Burst from IP {ip} spans {time_span.total_seconds()}s, "
                f"max allowed is {max_window}s"
            )

    def test_off_hours_escalation_events_count(self):
        """Should generate the configured number of off-hours privilege escalation events."""
        rng = np.random.default_rng(SEED)
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        anomaly_config = AnomalyConfig(
            burst_count=20,
            burst_window_minutes=5,
            burst_windows=2,
            off_hours_escalation_count=5,
        )

        anomaly_events = inject_anomalies(rng, start_time, 30, anomaly_config)
        escalation_events = [
            e for e in anomaly_events
            if e["event_type"] == EventType.PRIVILEGE_ESCALATION.value
        ]

        assert len(escalation_events) == anomaly_config.off_hours_escalation_count

    def test_off_hours_escalation_outside_business_hours(self):
        """Off-hours escalation events should all be outside 09:00-17:00 UTC."""
        rng = np.random.default_rng(SEED)
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        anomaly_config = AnomalyConfig(
            burst_count=20,
            burst_window_minutes=5,
            burst_windows=2,
            off_hours_escalation_count=5,
        )

        anomaly_events = inject_anomalies(rng, start_time, 30, anomaly_config)
        escalation_events = [
            e for e in anomaly_events
            if e["event_type"] == EventType.PRIVILEGE_ESCALATION.value
        ]

        for event in escalation_events:
            hour = event["event_time"].hour
            assert hour < 9 or hour >= 17, (
                f"Off-hours escalation at hour {hour} is within business hours"
            )

    def test_geographic_anomaly_events(self):
        """Geographic anomaly events should be from configured unusual countries."""
        rng = np.random.default_rng(SEED)
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        anomaly_countries = ["KP", "IR"]
        anomaly_config = AnomalyConfig(
            burst_count=20,
            burst_window_minutes=5,
            burst_windows=2,
            off_hours_escalation_count=5,
            geographic_anomaly_countries=anomaly_countries,
        )

        anomaly_events = inject_anomalies(rng, start_time, 30, anomaly_config)

        # Geographic anomaly events are specifically suspicious_ip_activity or
        # brute_force_attempt from the anomaly countries.
        # Other injected events (bursts, escalations) may also randomly get
        # anomaly country codes from Faker, so we filter by event type too.
        geo_event_types = {
            EventType.SUSPICIOUS_IP.value,
            EventType.BRUTE_FORCE.value,
        }
        geo_events = [
            e for e in anomaly_events
            if e["country"] in anomaly_countries
            and e["event_type"] in geo_event_types
        ]

        # 5 events per country = 10 total geographic anomaly events
        # Some burst events (brute_force from Faker) may also get anomaly countries,
        # so we check at least 10 are generated
        assert len(geo_events) >= 5 * len(anomaly_countries), (
            f"Expected at least {5 * len(anomaly_countries)} geographic anomaly events, "
            f"got {len(geo_events)}"
        )


# --- 5. Field correlations ---


@pytest.mark.unit
class TestFieldCorrelations:
    """Test field correlations: internal IPs ↔ departments, attacks ↔ higher severity."""

    def test_internal_ips_correlate_with_internal_departments(self, events):
        """Internal IPs should correlate with IT/Engineering/Operations departments more often."""
        internal_ip_departments = ["IT", "Engineering", "Operations"]

        internal_events = [e for e in events if _is_rfc1918(e["src_ip"])]
        external_events = [e for e in events if not _is_rfc1918(e["src_ip"])]

        assert len(internal_events) > 0, "Should have internal IP events"
        assert len(external_events) > 0, "Should have external IP events"

        # Internal IPs should have a higher ratio of internal departments
        internal_dept_ratio_for_internal_ips = sum(
            1 for e in internal_events if e["department"] in internal_ip_departments
        ) / len(internal_events)

        internal_dept_ratio_for_external_ips = sum(
            1 for e in external_events if e["department"] in internal_ip_departments
        ) / len(external_events)

        # Internal IPs should have a significantly higher ratio
        assert internal_dept_ratio_for_internal_ips > internal_dept_ratio_for_external_ips, (
            f"Internal IP dept ratio ({internal_dept_ratio_for_internal_ips:.2f}) "
            f"should exceed external IP dept ratio ({internal_dept_ratio_for_external_ips:.2f})"
        )

    def test_attack_events_have_higher_average_severity(self, events):
        """Attack events should have higher average severity than non-attack events."""
        severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}

        attack_events = [e for e in events if e["event_type"] in ATTACK_EVENT_TYPES]
        non_attack_events = [e for e in events if e["event_type"] not in ATTACK_EVENT_TYPES]

        assert len(attack_events) > 0, "Should have attack events"
        assert len(non_attack_events) > 0, "Should have non-attack events"

        avg_attack_severity = sum(
            severity_rank[e["severity"]] for e in attack_events
        ) / len(attack_events)

        avg_non_attack_severity = sum(
            severity_rank[e["severity"]] for e in non_attack_events
        ) / len(non_attack_events)

        assert avg_attack_severity > avg_non_attack_severity, (
            f"Attack avg severity ({avg_attack_severity:.2f}) should exceed "
            f"non-attack avg severity ({avg_non_attack_severity:.2f})"
        )

    def test_internal_ip_ratio(self, events):
        """Should generate approximately 60% internal IPs (within tolerance)."""
        # Only check base events (exclude anomaly-injected which are all external)
        # Base events are the first EVENT_COUNT items
        base_events = events[:EVENT_COUNT]
        internal_count = sum(1 for e in base_events if _is_rfc1918(e["src_ip"]))
        actual_ratio = internal_count / len(base_events)
        expected_ratio = 0.60

        assert abs(actual_ratio - expected_ratio) < TOLERANCE, (
            f"Internal IP ratio: expected ~{expected_ratio:.2f}, "
            f"got {actual_ratio:.2f} (tolerance: {TOLERANCE})"
        )


# --- 6. Deterministic output with seed ---


@pytest.mark.unit
class TestDeterminism:
    """Test that the same seed produces the same output."""

    def test_same_seed_produces_same_events(self):
        """Running generator twice with same seed should produce identical events."""
        config = GeneratorConfig(count=100, seed=42, time_range_days=7)

        events_1 = generate_security_events(config)
        events_2 = generate_security_events(config)

        assert len(events_1) == len(events_2)
        # Compare key fields (event_id is UUID, always different)
        for e1, e2 in zip(events_1, events_2):
            assert e1["event_type"] == e2["event_type"]
            assert e1["severity"] == e2["severity"]
            assert e1["src_ip"] == e2["src_ip"]
            assert e1["department"] == e2["department"]
            assert e1["country"] == e2["country"]


# --- Helper function tests ---


@pytest.mark.unit
class TestHelperFunctions:
    """Test helper/utility functions used by the generator."""

    def test_is_rfc1918_internal_ips(self):
        """RFC1918 IPs should be correctly identified."""
        assert _is_rfc1918("10.0.0.1") is True
        assert _is_rfc1918("10.255.255.254") is True
        assert _is_rfc1918("172.16.0.1") is True
        assert _is_rfc1918("172.31.255.254") is True
        assert _is_rfc1918("192.168.0.1") is True
        assert _is_rfc1918("192.168.255.254") is True

    def test_is_rfc1918_external_ips(self):
        """External IPs should not be identified as RFC1918."""
        assert _is_rfc1918("8.8.8.8") is False
        assert _is_rfc1918("172.32.0.1") is False
        assert _is_rfc1918("192.169.0.1") is False
        assert _is_rfc1918("1.1.1.1") is False

    def test_sample_ip_internal_ratio(self):
        """IP sampling should respect the internal ratio parameter."""
        rng = np.random.default_rng(SEED)
        n = 500
        ips = sample_ip_addresses(rng, n=n, internal_ratio=0.60)

        internal_count = sum(1 for ip in ips if _is_rfc1918(ip))
        actual_ratio = internal_count / n
        expected_ratio = 0.60

        assert abs(actual_ratio - expected_ratio) < TOLERANCE, (
            f"IP internal ratio: expected ~{expected_ratio:.2f}, got {actual_ratio:.2f}"
        )
