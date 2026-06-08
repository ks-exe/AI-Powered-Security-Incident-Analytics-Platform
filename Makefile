.PHONY: setup generate-data ingest transform detect-anomalies run-pipeline test test-unit test-property test-integration lint docs docker-up docker-down clean

# Project setup (cross-platform)
setup:
	python -m venv venv
	python -m pip install -e ".[dev]"
	@echo "Setup complete. Activate with: source venv/bin/activate (Linux/Mac) or venv\\Scripts\\activate (Windows)"

# Data generation
generate-data:
	python -m mock_data.generator

# DLT ingestion pipeline
ingest:
	python -m dlt_pipeline.pipeline

# dbt transformations (Bronze -> Silver -> Gold)
transform:
	cd dbt_project && dbt build

# ML anomaly detection
detect-anomalies:
	python -m ml_detection.train
	python -m ml_detection.predict

# Run full pipeline end-to-end
run-pipeline: generate-data ingest transform detect-anomalies

# Testing
test: test-unit test-property test-integration

test-unit:
	pytest tests/unit/ -v -m unit

test-property:
	pytest tests/unit/ -v -m property

test-integration:
	pytest tests/integration/ -v -m integration

# Linting
lint:
	ruff check .
	ruff format --check .

# Documentation
docs:
	cd dbt_project && dbt docs generate && dbt docs serve --port 8081

# Docker services
docker-up:
	docker compose up -d

docker-down:
	docker compose down

# Clean generated artifacts
clean:
	rm -f mock_data/*.parquet mock_data/*.jsonl
	rm -f *.duckdb data/*.duckdb
	rm -rf __pycache__ **/__pycache__
	rm -rf models/*.joblib
	rm -rf logs/*.jsonl
	rm -rf .pytest_cache
	rm -rf dbt_project/target dbt_project/dbt_packages
