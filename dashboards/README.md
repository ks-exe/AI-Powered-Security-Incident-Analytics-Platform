# Dashboards — Import/Export Guide

This directory contains version-controlled Apache Superset dashboard configurations for the Security Incident Analytics Platform.

## Files

| File | Description |
|------|-------------|
| `security_overview.json` | Main Security Overview dashboard with KPI cards, charts, and filters |

## Importing a Dashboard

To import the dashboard into a running Superset instance:

```bash
superset import-dashboards -p dashboards/security_overview.json
```

Or via the Superset CLI inside Docker:

```bash
docker exec -it superset superset import-dashboards -p /app/dashboards/security_overview.json
```

### Prerequisites for Import

1. Superset must be running and initialized (admin user created, database connection configured)
2. The DuckDB database (`data/security_analytics.duckdb`) must contain the required tables:
   - `security_silver.kpi_summary`
   - `security_silver.attack_volume_by_day`
   - `security_silver.attack_volume_by_country`
   - `security_silver.silver_events`
   - `security_silver.anomaly_results`
3. The database connection "DuckDB Security Analytics" must be registered in Superset

## Exporting Dashboards

To export all dashboards from a running Superset instance:

```bash
superset export-dashboards -d dashboards/
```

Or via Docker:

```bash
docker exec -it superset superset export-dashboards -d /app/dashboards/
```

To export a specific dashboard by ID:

```bash
superset export-dashboards -d dashboards/ -i <dashboard_id>
```

## JSON Structure

The `security_overview.json` file uses Superset's native import/export format with the following top-level structure:

```
{
  "_metadata": {           // Export metadata (version, timestamp, type)
  "dashboard": {           // Dashboard definition
    "dashboard_title":     // Display title
    "slug":                // URL-friendly identifier
    "json_metadata": {     // Dashboard-level settings
      "native_filter_configuration": [...]  // Global filters
    },
    "position_json": {     // Layout grid (rows, columns, chart placement)
      "ROOT_ID": {...},
      "GRID_ID": {...},
      "ROW-*": {...},      // Row containers
      "CHART-*": {...}     // Chart placements with width/height
    }
  },
  "charts": [              // Chart (slice) definitions
    {
      "slice_name":        // Display name
      "chart_id":          // Unique chart identifier
      "viz_type":          // Visualization type (big_number_total, pie, etc.)
      "datasource": {...}, // Table/schema/database mapping
      "params": {...}      // Chart-specific configuration
    }
  ],
  "datasets": [            // Dataset definitions (table metadata)
    {
      "table_name":        // Source table name
      "schema":            // Database schema
      "sql":               // SQL query for the dataset
      "columns": [...]     // Column definitions with types
    }
  ],
  "databases": [           // Database connection definitions
    {
      "database_name":     // Connection display name
      "sqlalchemy_uri":    // SQLAlchemy connection string
      "extra": {...}       // Engine parameters (e.g., read_only)
    }
  ]
}
```

### How It Maps to Superset's Import Format

| JSON Section | Superset Concept | Purpose |
|---|---|---|
| `_metadata` | Export header | Versioning and identification |
| `dashboard.position_json` | Dashboard layout | Grid-based positioning (12-column grid) |
| `dashboard.json_metadata.native_filter_configuration` | Native filters | Cross-chart filter definitions |
| `charts[]` | Slices/Charts | Individual visualization configs |
| `charts[].datasource` | Chart data source | Links chart to dataset and Cube.js cube |
| `datasets[]` | Datasets | Table metadata and column definitions |
| `databases[]` | Database connections | Connection strings for data sources |

### Chart Types Used

| Chart ID | Superset `viz_type` | Description |
|---|---|---|
| `kpi_total_attacks` | `big_number_total` | KPI card — Total Attacks |
| `kpi_failed_login_rate` | `big_number_total` | KPI card — Failed Login Rate (%) |
| `kpi_avg_mttd` | `big_number_total` | KPI card — Avg MTTD (min) |
| `kpi_avg_mttr` | `big_number_total` | KPI card — Avg MTTR (min) |
| `kpi_sla_compliance` | `big_number_total` | KPI card — SLA Compliance (%) |
| `attack_volume_by_day` | `echarts_timeseries_line` | Time-series line chart |
| `attack_volume_by_country` | `echarts_timeseries_bar` | Horizontal bar chart (top 10) |
| `events_by_type` | `echarts_timeseries_bar` | Vertical bar chart (all 8 types) |
| `severity_distribution` | `pie` | Donut chart with percentage labels |
| `anomaly_timeline` | `echarts_timeseries_line` | Anomaly score with threshold line |

### Global Filters

The dashboard includes 4 native filters that apply to all charts:

1. **Date Range** — Filters by `event_time` (default: last 30 days)
2. **Event Type** — Multi-select filter on `event_type`
3. **Severity** — Multi-select filter on `severity`
4. **Country** — Multi-select filter on `country`

## Modifying the Dashboard

1. Make changes in the Superset UI
2. Export the updated dashboard: `superset export-dashboards -d dashboards/`
3. Commit the updated JSON to version control
4. Team members import with: `superset import-dashboards -p dashboards/security_overview.json`

## Troubleshooting

| Issue | Solution |
|---|---|
| Import fails with "database not found" | Register the DuckDB database connection first via Superset UI or init script |
| Charts show "No data" | Run `make transform` to populate Gold layer tables |
| Filters don't work | Verify dataset column names match filter target definitions |
| Layout appears broken | Clear browser cache; Superset caches dashboard layout |
