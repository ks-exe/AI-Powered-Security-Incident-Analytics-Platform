"""Statistical distribution functions for mock security event generation.

Provides sampling functions for severity, event type, temporal patterns, and IP
addresses. All functions accept a numpy random Generator instance for reproducible
random state and configuration parameters for customization.
"""

from datetime import datetime, timedelta, timezone

import numpy as np
from numpy.random import Generator

from mock_data.schemas import EventType, Severity

# Default severity weight distribution
DEFAULT_SEVERITY_WEIGHTS: dict[str, float] = {
    Severity.LOW.value: 0.40,
    Severity.MEDIUM.value: 0.30,
    Severity.HIGH.value: 0.20,
    Severity.CRITICAL.value: 0.10,
}

# Default event type weight distribution (configurable)
DEFAULT_EVENT_TYPE_WEIGHTS: dict[str, float] = {
    EventType.FAILED_LOGIN.value: 0.20,
    EventType.SUCCESSFUL_LOGIN.value: 0.25,
    EventType.MALWARE_ALERT.value: 0.08,
    EventType.PRIVILEGE_ESCALATION.value: 0.05,
    EventType.SUSPICIOUS_IP.value: 0.10,
    EventType.VPN_LOGIN.value: 0.15,
    EventType.ACCOUNT_LOCKOUT.value: 0.10,
    EventType.BRUTE_FORCE.value: 0.07,
}

# RFC1918 internal IP ranges
_RFC1918_RANGES = [
    ("10.0.0.0", "10.255.255.255"),       # 10.0.0.0/8
    ("172.16.0.0", "172.31.255.255"),      # 172.16.0.0/12
    ("192.168.0.0", "192.168.255.255"),    # 192.168.0.0/16
]

# Business hours: 09:00-17:00 UTC
_BUSINESS_HOUR_START = 9
_BUSINESS_HOUR_END = 17


def sample_severity(
    rng: Generator,
    n: int = 1,
    weights: dict[str, float] | None = None,
) -> list[str]:
    """Sample severity values according to weight distribution.

    Args:
        rng: NumPy random Generator instance for reproducibility.
        n: Number of severity values to sample.
        weights: Mapping of severity value to probability weight.
            Defaults to low=40%, medium=30%, high=20%, critical=10%.

    Returns:
        List of severity string values (e.g., ["low", "high", "medium"]).
    """
    if weights is None:
        weights = DEFAULT_SEVERITY_WEIGHTS

    severities = list(weights.keys())
    probabilities = np.array(list(weights.values()), dtype=np.float64)
    # Normalize in case weights don't sum to exactly 1.0
    probabilities = probabilities / probabilities.sum()

    indices = rng.choice(len(severities), size=n, p=probabilities)
    return [severities[i] for i in indices]


def sample_event_type(
    rng: Generator,
    n: int = 1,
    weights: dict[str, float] | None = None,
) -> list[str]:
    """Sample event type values according to weight distribution.

    Args:
        rng: NumPy random Generator instance for reproducibility.
        n: Number of event type values to sample.
        weights: Mapping of event type value to probability weight.
            If empty or None, uses default weights for all 8 event types.

    Returns:
        List of event type string values (e.g., ["failed_login", "vpn_login"]).
    """
    if not weights:
        weights = DEFAULT_EVENT_TYPE_WEIGHTS

    event_types = list(weights.keys())
    probabilities = np.array(list(weights.values()), dtype=np.float64)
    # Normalize in case weights don't sum to exactly 1.0
    probabilities = probabilities / probabilities.sum()

    indices = rng.choice(len(event_types), size=n, p=probabilities)
    return [event_types[i] for i in indices]


def sample_timestamps(
    rng: Generator,
    n: int = 1,
    start_time: datetime | None = None,
    time_range_days: int = 30,
    business_hour_ratio: float = 0.70,
) -> list[datetime]:
    """Sample event timestamps with business-hour clustering.

    Generates timestamps distributed across the specified time range with
    a configurable proportion falling during business hours (09:00-17:00 UTC).

    Args:
        rng: NumPy random Generator instance for reproducibility.
        n: Number of timestamps to generate.
        start_time: Start of the time range. Defaults to 30 days before now (UTC).
        time_range_days: Number of days the time range spans.
        business_hour_ratio: Proportion of events during 09:00-17:00 UTC.
            Default is 0.70 (70%).

    Returns:
        List of timezone-aware datetime objects (UTC).
    """
    if start_time is None:
        start_time = datetime.now(timezone.utc) - timedelta(days=time_range_days)

    total_seconds = time_range_days * 24 * 3600

    # Determine how many events fall in business hours vs off-hours
    n_business = int(n * business_hour_ratio)
    n_off_hours = n - n_business

    timestamps: list[datetime] = []

    # Generate business-hour timestamps (09:00-17:00 UTC)
    if n_business > 0:
        business_timestamps = _sample_within_hours(
            rng, n_business, start_time, time_range_days,
            _BUSINESS_HOUR_START, _BUSINESS_HOUR_END,
        )
        timestamps.extend(business_timestamps)

    # Generate off-hours timestamps (00:00-09:00 and 17:00-24:00 UTC)
    if n_off_hours > 0:
        off_hour_timestamps = _sample_outside_hours(
            rng, n_off_hours, start_time, time_range_days,
            _BUSINESS_HOUR_START, _BUSINESS_HOUR_END,
        )
        timestamps.extend(off_hour_timestamps)

    # Shuffle to avoid business-hour events always being first
    rng.shuffle(timestamps)
    return timestamps


def _sample_within_hours(
    rng: Generator,
    n: int,
    start_time: datetime,
    time_range_days: int,
    hour_start: int,
    hour_end: int,
) -> list[datetime]:
    """Sample timestamps within the specified hour range across multiple days."""
    timestamps = []
    hours_in_window = hour_end - hour_start  # 8 hours for business hours

    for _ in range(n):
        # Pick a random day in the range
        day_offset = int(rng.integers(0, time_range_days))
        # Pick a random second within the business hour window
        second_in_window = int(rng.integers(0, hours_in_window * 3600))

        ts = start_time.replace(
            hour=hour_start, minute=0, second=0, microsecond=0
        ) + timedelta(days=day_offset, seconds=second_in_window)
        timestamps.append(ts)

    return timestamps


def _sample_outside_hours(
    rng: Generator,
    n: int,
    start_time: datetime,
    time_range_days: int,
    hour_start: int,
    hour_end: int,
) -> list[datetime]:
    """Sample timestamps outside the specified hour range across multiple days."""
    timestamps = []
    # Off-hours: [0, hour_start) and [hour_end, 24)
    off_hours_seconds = (hour_start + (24 - hour_end)) * 3600  # 16 hours

    for _ in range(n):
        # Pick a random day in the range
        day_offset = int(rng.integers(0, time_range_days))
        # Pick a random second within the off-hours window
        second_in_window = int(rng.integers(0, off_hours_seconds))

        # Map to actual hour: first part [0, hour_start), second part [hour_end, 24)
        pre_business_seconds = hour_start * 3600
        if second_in_window < pre_business_seconds:
            # Falls in [0, hour_start)
            ts = start_time.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=day_offset, seconds=second_in_window)
        else:
            # Falls in [hour_end, 24)
            offset_from_end = second_in_window - pre_business_seconds
            ts = start_time.replace(
                hour=hour_end, minute=0, second=0, microsecond=0
            ) + timedelta(days=day_offset, seconds=offset_from_end)

        timestamps.append(ts)

    return timestamps


def sample_ip_addresses(
    rng: Generator,
    n: int = 1,
    internal_ratio: float = 0.60,
) -> list[str]:
    """Generate IP addresses with configured internal/external ratio.

    Internal IPs are from RFC1918 ranges:
      - 10.0.0.0/8
      - 172.16.0.0/12
      - 192.168.0.0/16

    External IPs are non-RFC1918 valid IPv4 addresses (excluding reserved ranges).

    Args:
        rng: NumPy random Generator instance for reproducibility.
        n: Number of IP addresses to generate.
        internal_ratio: Proportion of internal (RFC1918) IPs. Default is 0.60 (60%).

    Returns:
        List of IPv4 address strings.
    """
    n_internal = int(n * internal_ratio)
    n_external = n - n_internal

    ips: list[str] = []

    # Generate internal IPs
    if n_internal > 0:
        internal_ips = _generate_internal_ips(rng, n_internal)
        ips.extend(internal_ips)

    # Generate external IPs
    if n_external > 0:
        external_ips = _generate_external_ips(rng, n_external)
        ips.extend(external_ips)

    # Shuffle to mix internal and external
    rng.shuffle(ips)
    return ips


def _generate_internal_ips(rng: Generator, n: int) -> list[str]:
    """Generate RFC1918 internal IP addresses.

    Distributes across the three RFC1918 ranges:
      - 10.0.0.0/8 (50% of internal IPs)
      - 172.16.0.0/12 (25% of internal IPs)
      - 192.168.0.0/16 (25% of internal IPs)
    """
    ips = []
    # Distribution among RFC1918 ranges
    range_weights = np.array([0.50, 0.25, 0.25])
    range_indices = rng.choice(3, size=n, p=range_weights)

    for idx in range_indices:
        if idx == 0:
            # 10.0.0.0/8 — 10.x.x.x
            octets = [10, int(rng.integers(0, 256)), int(rng.integers(0, 256)),
                      int(rng.integers(1, 255))]
        elif idx == 1:
            # 172.16.0.0/12 — 172.16.x.x to 172.31.x.x
            octets = [172, int(rng.integers(16, 32)), int(rng.integers(0, 256)),
                      int(rng.integers(1, 255))]
        else:
            # 192.168.0.0/16 — 192.168.x.x
            octets = [192, 168, int(rng.integers(0, 256)),
                      int(rng.integers(1, 255))]

        ips.append(f"{octets[0]}.{octets[1]}.{octets[2]}.{octets[3]}")

    return ips


def _generate_external_ips(rng: Generator, n: int) -> list[str]:
    """Generate valid external (non-RFC1918) IPv4 addresses.

    Avoids RFC1918 private ranges, loopback (127.x), link-local (169.254.x),
    multicast (224-239), and reserved (240+) ranges.
    """
    ips = []

    # Valid first octets for external IPs (excluding private/reserved)
    # Avoid: 0, 10, 127, 169, 172(16-31), 192(168), 224-255
    valid_first_octets = [
        o for o in range(1, 224)
        if o not in (0, 10, 127, 169)
    ]

    for _ in range(n):
        while True:
            first = int(rng.choice(valid_first_octets))
            second = int(rng.integers(0, 256))
            third = int(rng.integers(0, 256))
            fourth = int(rng.integers(1, 255))

            # Exclude 172.16-31.x.x and 192.168.x.x
            if first == 172 and 16 <= second <= 31:
                continue
            if first == 192 and second == 168:
                continue
            # Exclude link-local 169.254.x.x
            if first == 169 and second == 254:
                continue

            ips.append(f"{first}.{second}.{third}.{fourth}")
            break

    return ips
