"""Model training module for anomaly detection.

Trains an IsolationForest model on feature vectors extracted from hourly
event summaries and saves the model artifact with a versioned filename.

Requirements: 9.6, 9.7, 9.8, 9.10
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ml_detection.features import FEATURE_COLUMNS
from scripts.logging_config import get_logger

logger = get_logger("ml_detection.train")


@dataclass
class TrainingConfig:
    """Configuration for IsolationForest training."""

    n_estimators: int = 100
    contamination: float = 0.05
    random_state: int = 42
    model_dir: Path = field(default_factory=lambda: Path("models"))


@dataclass
class TrainingResult:
    """Results from a model training run."""

    model_path: Path
    model_version: str
    n_samples_trained: int
    n_anomalies_detected: int
    anomaly_percentage: float
    training_duration_seconds: float
    contamination_parameter: float
    n_estimators: int


def train_model(
    features_df: pd.DataFrame,
    config: TrainingConfig = None,
) -> TrainingResult:
    """Train an IsolationForest model on feature vectors.

    Fits an IsolationForest with the configured parameters, saves the model
    artifact to disk with a versioned filename, and validates that the
    anomaly percentage is within an acceptable range (1%–15%).

    Args:
        features_df: DataFrame containing FEATURE_COLUMNS. Each row is one
            hourly time window.
        config: Training configuration. Uses defaults if None.

    Returns:
        TrainingResult with model path, version, and training metrics.

    Raises:
        ValueError: If features_df is empty or missing required columns.
    """
    if config is None:
        config = TrainingConfig()

    if features_df.empty:
        raise ValueError("Cannot train on empty feature DataFrame")

    missing_cols = set(FEATURE_COLUMNS) - set(features_df.columns)
    if missing_cols:
        raise ValueError(f"Missing feature columns: {sorted(missing_cols)}")

    logger.info(
        "Starting model training",
        extra={
            "context": {
                "n_samples": len(features_df),
                "n_estimators": config.n_estimators,
                "contamination": config.contamination,
            }
        },
    )

    # Extract feature matrix
    X = features_df[FEATURE_COLUMNS].values

    # Train IsolationForest
    start_time = time.time()
    model = IsolationForest(
        n_estimators=config.n_estimators,
        contamination=config.contamination,
        random_state=config.random_state,
    )
    model.fit(X)
    training_duration = time.time() - start_time

    # Get predictions to compute anomaly statistics
    predictions = model.predict(X)
    n_anomalies = int(np.sum(predictions == -1))
    anomaly_percentage = (n_anomalies / len(X)) * 100.0

    # Validate anomaly percentage
    if anomaly_percentage < 1.0 or anomaly_percentage > 15.0:
        logger.warning(
            "Anomaly percentage outside expected range (1%–15%)",
            extra={
                "context": {
                    "anomaly_percentage": round(anomaly_percentage, 2),
                    "n_anomalies": n_anomalies,
                    "n_samples": len(X),
                }
            },
        )

    # Save model artifact with versioned filename
    config.model_dir.mkdir(parents=True, exist_ok=True)
    model_version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    model_filename = f"isolation_forest_v{model_version}.joblib"
    model_path = config.model_dir / model_filename

    joblib.dump(model, model_path)

    result = TrainingResult(
        model_path=model_path,
        model_version=model_version,
        n_samples_trained=len(X),
        n_anomalies_detected=n_anomalies,
        anomaly_percentage=round(anomaly_percentage, 2),
        training_duration_seconds=round(training_duration, 3),
        contamination_parameter=config.contamination,
        n_estimators=config.n_estimators,
    )

    logger.info(
        "Model training complete",
        extra={
            "context": {
                "model_path": str(result.model_path),
                "model_version": result.model_version,
                "n_samples_trained": result.n_samples_trained,
                "n_anomalies_detected": result.n_anomalies_detected,
                "anomaly_percentage": result.anomaly_percentage,
                "training_duration_seconds": result.training_duration_seconds,
                "contamination_parameter": result.contamination_parameter,
                "n_estimators": result.n_estimators,
            }
        },
    )

    return result
