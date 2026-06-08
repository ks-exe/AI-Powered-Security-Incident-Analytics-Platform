FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    dagster \
    dagster-webserver \
    dagster-duckdb \
    duckdb \
    dlt[duckdb] \
    dbt-duckdb \
    faker \
    numpy \
    pandas \
    pydantic \
    scikit-learn \
    joblib \
    pyyaml

# Copy the full project
COPY . .

# Expose Dagster webserver port
EXPOSE 3000

# Default command runs the webserver
CMD ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000", "-w", "dagster_pipeline/workspace.yaml"]
