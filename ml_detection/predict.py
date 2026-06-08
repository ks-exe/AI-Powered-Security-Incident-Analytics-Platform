"""Model prediction module for anomaly detection.

Scores feature vectors using a trained IsolationForest model, assigns
anomaly scores and flags, computes contributing features, and persists
results to the Gold layer.

Requirements: 9.3, 9.4, 9.5, 9.9
"""

from dataclasses import dataclass
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ml_detection.features import FEATURE_COLUMNS
from scripts.logging_config import get_logger

logger = get_logger("ml_detection.predict")


@dataclass
class PredictionResult:
    """Results from anomaly prediction."""

    results_df: pd.DataFrame
    n_anomalies: int
    anomaly_percentage: float


def predict_anomalies(
    features_df: pd.DataFrame,
    model_path: Path,
    threshold: float = -0.5,
) -> PredictionResult:
    """Score feature vectors using a trained IsolationForest model.

    Assigns an anomaly_score in the range [-1, 1] to each time window and
    sets the is_anomaly flag based on whether the score is below the threshold.
    For anomalous windows, computes the top contributing feature via
    permutation importance.

    Args:
        features_df: DataFrame with FEATURE_COLUMNS plus window_start/window_end.
        model_path: Path to the saved joblib model file.
        threshold: Score threshold for anomaly classification. Windows with
            anomaly_score < threshold are flagged as anomalies. Default: -0.5.

    Returns:
        PredictionResult containing the scored DataFrame, count and percentage
        of anomalies.

    Raises:
        FileNotFoundError: If model_path does not exist.
        ValueError: If features_df is empty or missing required columns.
    """
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    if features_df.empty:
        raise ValueError("Cannot predict on empty feature DataFrame")

    missing_cols = set(FEATURE_COLUMNS) - set(features_df.columns)
    if missing_cols:
        raise ValueError(f"Missing feature columns: {sorted(missing_cols)}")

    logger.info(
        "Loading model and scoring features",
        extra={
            "context": {
                "model_path": str(model_path),
                "n_windows": len(features_df),
                "threshold": threshold,
            }
        },
    )

    # Load model
    model: IsolationForest = joblib.load(model_path)

    # Extract feature matrix
    X = features_df[FEATURE_COLUMNS].values

    # Score all windows using decision_function (higher = more normal)
    raw_scores = model.decision_function(X)

    # Normalize scores to [-1, 1] range
    # decision_function returns values where negative = more anomalous
    # We normalize so -1 is most anomalous, +1 is most normal
    score_min = raw_scores.min()
    score_max = raw_scores.max()
    if score_max - score_min > 0:
        anomaly_scores = 2.0 * (raw_scores - score_min) / (score_max - score_min) - 1.0
    else:
        anomaly_scores = np.zeros_like(raw_scores)

    # Apply threshold to determine anomaly flag
    is_anomaly = anomaly_scores < threshold

    # Build results DataFrame
    results_df = features_df[["window_start", "window_end"]].copy()
    results_df["anomaly_score"] = anomaly_scores
    results_df["is_anomaly"] = is_anomaly

    # Compute top contributing feature for anomalous windows
    results_df["top_contributing_feature"] = _compute_top_features(
        model, X, is_anomaly, FEATURE_COLUMNS
    )

    # Add feature values to results for reference
    for col in FEATURE_COLUMNS:
        results_df[col] = features_df[col].values

    n_anomalies = int(is_anomaly.sum())
    anomaly_percentage = (n_anomalies / len(features_df)) * 100.0

    logger.info(
        "Prediction complete",
        extra={
            "context": {
                "n_anomalies": n_anomalies,
                "anomaly_percentage": round(anomaly_percentage, 2),
                "threshold": threshold,
            }
        },
    )

    return PredictionResult(
        results_df=results_df,
        n_anomalies=n_anomalies,
        anomaly_percentage=round(anomaly_percentage, 2),
    )


def _compute_top_features(
    model: IsolationForest,
    X: np.ndarray,
    is_anomaly: np.ndarray,
    feature_names: list[str],
) -> list[str]:
    """Compute top contributing feature for each window via permutation importance.

    For anomalous windows, permutes each feature independently and measures
    the change in anomaly score. The feature causing the largest score increase
    when permuted is the top contributor.

    For non-anomalous windows, returns "none".

    Args:
        model: Trained IsolationForest model.
        X: Feature matrix (n_samples x n_features).
        is_anomaly: Boolean array indicating which windows are anomalous.
        feature_names: List of feature column names.

    Returns:
        List of feature names (one per window).
    """
    top_features = ["none"] * len(X)
    anomaly_indices = np.where(is_anomaly)[0]

    if len(anomaly_indices) == 0:
        return top_features

    # Get baseline scores for anomalous windows
    baseline_scores = model.decision_function(X[anomaly_indices])

    # For each feature, permute and measure score change
    rng = np.random.default_rng(42)
    importance_matrix = np.zeros((len(anomaly_indices), len(feature_names)))

    for feat_idx in range(len(feature_names)):
        X_permuted = X[anomaly_indices].copy()
        # Shuffle the feature values across the anomalous samples
        X_permuted[:, feat_idx] = rng.permutation(X_permuted[:, feat_idx])
        permuted_scores = model.decision_function(X_permuted)
        # Higher score after permutation means the feature was contributing to anomaly
        importance_matrix[:, feat_idx] = permuted_scores - baseline_scores

    # Assign top feature for each anomalous window
    for i, idx in enumerate(anomaly_indices):
        top_feat_idx = np.argmax(importance_matrix[i])
        top_features[idx] = feature_names[top_feat_idx]

    return top_features


def persist_results(
    results: PredictionResult,
    db_path: Path,
    model_version: str,
) -> int:
    """Write anomaly results to the Gold layer anomaly_results table.

    Creates or replaces the anomaly_results table in the security_gold schema
    with the prediction results plus model metadata.

    Args:
        results: PredictionResult containing the scored DataFrame.
        db_path: Path to the DuckDB database file.
        model_version: Version string of the model used for predictions.

    Returns:
        Number of rows written.

    Raises:
        FileNotFoundError: If db_path does not exist.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    df = results.results_df.copy()
    df["model_version"] = model_version

    logger.info(
        "Persisting anomaly results",
        extra={
            "context": {
                "db_path": str(db_path),
                "n_rows": len(df),
                "model_version": model_version,
            }
        },
    )

    con = duckdb.connect(str(db_path))
    try:
        # Ensure schema exists
        con.execute("CREATE SCHEMA IF NOT EXISTS security_gold")

        # Create or replace the anomaly_results table
        con.execute("DROP TABLE IF EXISTS security_gold.anomaly_results")
        con.execute("""
            CREATE TABLE security_gold.anomaly_results AS
            SELECT * FROM df
        """)

        rows_written = con.execute(
            "SELECT COUNT(*) FROM security_gold.anomaly_results"
        ).fetchone()[0]
    finally:
        con.close()

    logger.info(
        "Anomaly results persisted",
        extra={"context": {"rows_written": rows_written}},
    )

    return rows_written
