"""Feature engineering module for anomaly detection.

Extracts feature vectors from the Silver layer by computing hourly aggregations
of security events. Each row in the output DataFrame represents one hourly
time window with 10 computed features.

Requirements: 9.2
"""

import duckdb
import pandas as pd
from pathlib import Path

from scripts.logging_config import get_logger

logger = get_logger("ml_detection.features")

FEATURE_COLUMNS = [
    "total_event_count",
    "unique_src_ips",
    "unique_users",
    "failed_login_count",
    "failed_login_ratio",
    "attack_event_count",
    "avg_severity_rank",
    "critical_event_count",
    "unique_countries",
    "events_outside_business_hours_ratio",
]


def extract_features(db_path: Path) -> pd.DataFrame:
    """Extract feature vectors from Silver layer events via hourly aggregation.

    Queries the security_silver.silver_events table in DuckDB and computes
    10 features per hourly time window.

    Args:
        db_path: Path to the DuckDB database file.

    Returns:
        DataFrame with columns: window_start, window_end, plus all FEATURE_COLUMNS.
        Each row represents one hourly time window.

    Raises:
        FileNotFoundError: If db_path does not exist.
        RuntimeError: If the query fails or returns no data.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    logger.info(
        "Extracting features from Silver layer",
        extra={"context": {"db_path": str(db_path)}},
    )

    query = """
    SELECT
        DATE_TRUNC('hour', event_time) AS window_start,
        DATE_TRUNC('hour', event_time) + INTERVAL '1 hour' AS window_end,
        COUNT(*) AS total_event_count,
        COUNT(DISTINCT src_ip) AS unique_src_ips,
        COUNT(DISTINCT username) AS unique_users,
        COUNT(*) FILTER (WHERE event_type = 'failed_login') AS failed_login_count,
        CAST(COUNT(*) FILTER (WHERE event_type = 'failed_login') AS FLOAT)
            / NULLIF(COUNT(*), 0) AS failed_login_ratio,
        COUNT(*) FILTER (WHERE is_attack_event) AS attack_event_count,
        AVG(severity_rank) AS avg_severity_rank,
        COUNT(*) FILTER (WHERE severity = 'critical') AS critical_event_count,
        COUNT(DISTINCT country) AS unique_countries,
        CAST(COUNT(*) FILTER (WHERE NOT is_business_hours) AS FLOAT)
            / NULLIF(COUNT(*), 0) AS events_outside_business_hours_ratio
    FROM security_silver.silver_events
    GROUP BY DATE_TRUNC('hour', event_time)
    ORDER BY window_start
    """

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        features_df = con.execute(query).fetchdf()
    finally:
        con.close()

    if features_df.empty:
        raise RuntimeError("Feature extraction returned no data. Is the Silver layer populated?")

    # Fill any NaN values with 0 for ratio columns where NULLIF produced NULL
    features_df[FEATURE_COLUMNS] = features_df[FEATURE_COLUMNS].fillna(0.0)

    logger.info(
        "Feature extraction complete",
        extra={
            "context": {
                "n_windows": len(features_df),
                "time_range_start": str(features_df["window_start"].min()),
                "time_range_end": str(features_df["window_end"].max()),
            }
        },
    )

    return features_df


def validate_features(features_df: pd.DataFrame) -> bool:
    """Validate that a feature DataFrame has expected columns and no NaN values.

    Args:
        features_df: DataFrame to validate.

    Returns:
        True if validation passes.

    Raises:
        ValueError: If validation fails with details about what's wrong.
    """
    if features_df.empty:
        raise ValueError("Feature DataFrame is empty")

    # Check all expected feature columns are present
    missing_cols = set(FEATURE_COLUMNS) - set(features_df.columns)
    if missing_cols:
        raise ValueError(f"Missing feature columns: {sorted(missing_cols)}")

    # Check window columns are present
    for col in ["window_start", "window_end"]:
        if col not in features_df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Check for NaN values in feature columns
    nan_counts = features_df[FEATURE_COLUMNS].isna().sum()
    cols_with_nan = nan_counts[nan_counts > 0]
    if not cols_with_nan.empty:
        raise ValueError(
            f"NaN values found in feature columns: {dict(cols_with_nan)}"
        )

    logger.info(
        "Feature validation passed",
        extra={"context": {"n_rows": len(features_df), "n_features": len(FEATURE_COLUMNS)}},
    )
    return True
