# Troubleshooting

## Common Issues

### Pipeline Errors

| Issue | Cause | Solution |
|-------|-------|----------|
| `make generate-data` fails | Missing dependencies | Run `make setup` first |
| `make ingest` fails | No mock data | Run `make generate-data` first |
| `make transform` fails | No Bronze data | Run `make ingest` first |
| dbt tests fail | Stale data | Run `make run-pipeline` for fresh data |
| Import errors | Wrong environment | Activate venv: `source venv/bin/activate` |

### Docker Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Services won't start | Insufficient RAM | Need 16GB+; use lite profile for dev |
| Port conflicts | Ports already in use | Change ports in `.env` file |
| Health check fails | Service still starting | Wait 60s for Superset, 30s for others |
| Permission denied | Volume permissions | Run `docker compose down -v` and restart |

### Database Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Table not found" | Pipeline not run | Execute `make run-pipeline` |
| Duplicate records | Stale DLT state | Delete `.dlt/` directory and re-run |
| Schema mismatch | dbt version change | Run `dbt clean && dbt deps && dbt build` |

### ML/Anomaly Detection

| Issue | Cause | Solution |
|-------|-------|----------|
| "Feature extraction returned no data" | Silver layer empty | Run `make transform` first |
| Low precision/recall | Small dataset | Generate more data (increase count in config.yaml) |
| Model file not found | Training not run | Run `make detect-anomalies` |

## Useful Commands

```bash
# Check service health
./scripts/health_check.sh

# View pipeline logs
cat logs/pipeline_runs.jsonl | python -m json.tool

# Query DuckDB directly
python -c "import duckdb; print(duckdb.connect('data/security_analytics.duckdb').execute('SHOW TABLES').fetchall())"

# Reset everything
make clean
make run-pipeline
```
