"""Shared Dagster resources for the Security Analytics pipeline.

Provides DuckDB connection resource and dbt resource configuration.
"""

from pathlib import Path

from dagster import ConfigurableResource


class DuckDBResource(ConfigurableResource):
    """DuckDB database connection resource.

    Attributes:
        database_path: Path to the DuckDB database file.
    """

    database_path: str = "data/security_analytics.duckdb"

    def get_connection(self):
        """Get a DuckDB connection."""
        import duckdb

        return duckdb.connect(self.database_path)


class DbtResource(ConfigurableResource):
    """dbt project resource for running dbt CLI commands.

    Attributes:
        project_dir: Path to the dbt project directory.
        profiles_dir: Path to the dbt profiles directory.
        target: dbt target profile name.
    """

    project_dir: str = "dbt_project"
    profiles_dir: str = "dbt_project"
    target: str = "dev"

    def run(self, *args: str) -> "subprocess.CompletedProcess[str]":
        """Run a dbt CLI command.

        Args:
            *args: dbt CLI arguments (e.g., "run", "--select", "silver_events").

        Returns:
            CompletedProcess result with stdout and stderr.

        Raises:
            subprocess.CalledProcessError: If dbt command fails.
        """
        import subprocess

        cmd = [
            "dbt",
            *args,
            "--project-dir",
            self.project_dir,
            "--profiles-dir",
            self.profiles_dir,
            "--target",
            self.target,
        ]
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )


# Pre-configured resource instances
duckdb_resource = DuckDBResource(database_path="data/security_analytics.duckdb")
dbt_resource = DbtResource(
    project_dir="dbt_project",
    profiles_dir="dbt_project",
    target="dev",
)
