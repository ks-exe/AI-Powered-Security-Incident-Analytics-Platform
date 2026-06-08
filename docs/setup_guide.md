# Setup Guide

## Prerequisites

- Python 3.11+
- Docker Engine 24+ and Docker Compose v2+
- 16 GB RAM minimum
- 20 GB available disk space
- Git

## Installation

### 1. Clone and Setup

```bash
git clone <repository-url>
cd security-incident-analytics-platform
make setup
```

This creates a virtual environment and installs all Python dependencies.

### 2. Activate Environment

```bash
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Generate Mock Data

```bash
make generate-data
```

Produces ~10,000 synthetic security events in `mock_data/security_events.jsonl` and `.parquet`.

### 4. Run Pipeline (MVP)

```bash
make run-pipeline
```

Runs: data generation → DLT ingestion → dbt transformations → anomaly detection.

### 5. Start Docker Services (Full Platform)

```bash
# Validate prerequisites
./scripts/setup.sh

# Start all services
make docker-up
```

### 6. Access UIs

| Service | URL | Credentials |
|---------|-----|-------------|
| Superset | http://localhost:8088 | admin / admin123 |
| Dagster | http://localhost:3000 | — |
| Cube.js Playground | http://localhost:4000 | — |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin123 |

## Configuration

Copy `.env.example` to `.env` and adjust values:

```bash
cp .env.example .env
```

Key settings: MINIO credentials, SUPERSET secret key, CUBEJS API secret.

## Running Tests

```bash
make test          # All tests
make test-unit     # Unit tests only
make test-property # Property-based tests only
make lint          # Linting with ruff
```
