"""Model evaluation module for anomaly detection.

Computes precision and recall of the anomaly detection model against
known injected anomaly patterns. Logs metrics and validates against
target thresholds.

Requirements: 9.10
"""

import numpy as np
import pandas as pd

from scripts.logging_config import get_logger

logger = get_logger("ml_detection.evaluate")


def evaluate_model(
    results_df: pd.DataFrame,
    known_anomaly_windows: pd.DataFrame,
    window_col: str = "window_start",
) -> dict[str, float]:
    """Evaluate anomaly detection against known injected anomaly patterns.

    Computes precision (fraction of flagged windows that are true anomalies)
    and recall (fraction of true anomaly windows that are flagged).

    Args:
        results_df: Prediction results DataFrame with at least 'window_start'
            and 'is_anomaly' columns.
        known_anomaly_windows: DataFrame with 'window_start' column indicating
            time windows where anomalies were injected.
        window_col: Column name for the time window identifier.

    Returns:
        Dictionary with 'precision' and 'recall' values between 0.0 and 1.0.

    Raises:
        ValueError: If required columns are missing from input DataFrames.
    """
    if window_col not in results_df.columns:
        raise ValueError(f"results_df missing required column: {window_col}")
    if "is_anomaly" not in results_df.columns:
        raise ValueError("results_df missing required column: is_anomaly")
    if window_col not in known_anomaly_windows.columns:
        raise ValueError(f"known_anomaly_windows missing required column: {window_col}")

    # Get flagged windows (predicted anomalies)
    flagged_windows = set(
        results_df.loc[results_df["is_anomaly"], window_col].values
    )

    # Get true anomaly windows (injected patterns)
    true_anomaly_windows = set(known_anomaly_windows[window_col].values)

    # Compute precision: true positives / all flagged
    if len(flagged_windows) == 0:
        precision = 0.0
    else:
        true_positives = flagged_windows & true_anomaly_windows
        precision = len(true_positives) / len(flagged_windows)

    # Compute recall: true positives / all true anomalies
    if len(true_anomaly_windows) == 0:
        recall = 0.0
    else:
        true_positives = flagged_windows & true_anomaly_windows
        recall = len(true_positives) / len(true_anomaly_windows)

    metrics = {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
    }

    # Log metrics with target comparison
    precision_target = 0.7
    recall_target = 0.6

    logger.info(
        "Model evaluation complete",
        extra={
            "context": {
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "precision_target": precision_target,
                "recall_target": recall_target,
                "precision_meets_target": precision >= precision_target,
                "recall_meets_target": recall >= recall_target,
                "n_flagged_windows": len(flagged_windows),
                "n_true_anomaly_windows": len(true_anomaly_windows),
                "n_true_positives": len(flagged_windows & true_anomaly_windows),
            }
        },
    )

    if precision < precision_target:
        logger.warning(
            f"Precision {precision:.4f} below target {precision_target}",
            extra={"context": {"precision": precision, "target": precision_target}},
        )

    if recall < recall_target:
        logger.warning(
            f"Recall {recall:.4f} below target {recall_target}",
            extra={"context": {"recall": recall, "target": recall_target}},
        )

    return metrics


def compute_confusion_matrix(
    results_df: pd.DataFrame,
    known_anomaly_windows: pd.DataFrame,
    window_col: str = "window_start",
) -> dict[str, int]:
    """Compute confusion matrix components for the anomaly detection results.

    Args:
        results_df: Prediction results DataFrame with 'window_start' and 'is_anomaly'.
        known_anomaly_windows: DataFrame with 'window_start' for true anomaly windows.
        window_col: Column name for the time window identifier.

    Returns:
        Dictionary with true_positives, false_positives, true_negatives,
        false_negatives counts.
    """
    all_windows = set(results_df[window_col].values)
    flagged_windows = set(
        results_df.loc[results_df["is_anomaly"], window_col].values
    )
    true_anomaly_windows = set(known_anomaly_windows[window_col].values)

    true_positives = flagged_windows & true_anomaly_windows
    false_positives = flagged_windows - true_anomaly_windows
    false_negatives = true_anomaly_windows - flagged_windows
    true_negatives = (all_windows - flagged_windows) - true_anomaly_windows

    confusion = {
        "true_positives": len(true_positives),
        "false_positives": len(false_positives),
        "true_negatives": len(true_negatives),
        "false_negatives": len(false_negatives),
    }

    logger.info(
        "Confusion matrix computed",
        extra={"context": confusion},
    )

    return confusion
