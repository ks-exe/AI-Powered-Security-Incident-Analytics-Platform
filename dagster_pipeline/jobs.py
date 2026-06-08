"""Pipeline job definitions for the Security Analytics pipeline.

Defines the main security_analytics_pipeline job that materializes
all assets in dependency order.

Requirements: 8.1, 8.5
"""

from dagster import AssetSelection, define_asset_job

# Main pipeline job - selects all assets for full end-to-end execution
security_analytics_pipeline = define_asset_job(
    name="security_analytics_pipeline",
    selection=AssetSelection.all(),
    description=(
        "Full security analytics pipeline: generate mock data → ingest to Bronze → "
        "transform to Silver → compute Gold KPIs → run anomaly detection"
    ),
)
