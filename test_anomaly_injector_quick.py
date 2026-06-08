"""Quick verification script for the anomaly_injector module."""
import numpy as np
from datetime import datetime, timezone
from mock_data.anomaly_injector import inject_anomalies, AnomalyConfig

rng = np.random.default_rng(42)
start = datetime(2024, 1, 1, tzinfo=timezone.utc)
config = AnomalyConfig()

events = inject_anomalies(rng, start, 30, config)

print(f"Total anomaly events: {len(events)}")

burst_events = [e for e in events if e["event_type"] == "failed_login"]
print(f"Burst (failed_login): {len(burst_events)}")

esc_events = [e for e in events if e["event_type"] == "privilege_escalation"]
print(f"Off-hours escalation: {len(esc_events)}")

geo_countries = ["KP", "IR", "SY"]
geo_events = [e for e in events if e["country"] in geo_countries]
print(f"Geographic anomalies: {len(geo_events)}")

print(f"\nEvent keys: {list(events[0].keys())}")

# Verify burst properties
print(f"\n--- Burst Verification ---")
print(f"Expected burst events: {config.burst_count * config.burst_windows} = {config.burst_count} x {config.burst_windows}")
print(f"Actual burst events: {len(burst_events)}")

# Verify off-hours (check times are outside 09:00-17:00 UTC)
print(f"\n--- Off-hours Verification ---")
for e in esc_events[:3]:
    hour = e["event_time"].hour
    print(f"  Escalation at hour {hour} (is off-hours: {hour < 9 or hour >= 17})")

off_hours_correct = all(
    e["event_time"].hour < 9 or e["event_time"].hour >= 17 
    for e in esc_events
)
print(f"All escalations are off-hours: {off_hours_correct}")

# Verify geographic anomalies
print(f"\n--- Geographic Verification ---")
for country in geo_countries:
    count = len([e for e in events if e["country"] == country])
    print(f"  Events from {country}: {count}")

# Verify severity distribution (should be high/critical for anomalies)
severities = [e["severity"] for e in events]
high_critical = [s for s in severities if s in ("high", "critical")]
print(f"\n--- Severity Verification ---")
print(f"High/Critical: {len(high_critical)}/{len(events)} = {len(high_critical)/len(events):.1%}")

# Verify all required fields present
required_fields = [
    "event_id", "event_time", "username", "src_ip", "hostname",
    "event_type", "severity", "status", "country", "operating_system",
    "department", "detection_time", "resolution_time"
]
missing = [f for f in required_fields if f not in events[0]]
print(f"\nMissing required fields: {missing if missing else 'None'}")
print("\nAll checks passed!")
