"""Security Incident Analytics Platform — Interactive Dashboard

Run with: streamlit run dashboard.py
"""

import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Page config
st.set_page_config(
    page_title="Security Analytics Dashboard",
    page_icon="🛡️",
    layout="wide",
)

DB_PATH = "data/security_analytics.duckdb"
PROJECT_ROOT = Path(__file__).parent


def run_pipeline():
    """Re-run the full data pipeline: generate → ingest → transform → detect anomalies."""
    python = sys.executable
    steps = [
        ("Generating new mock data...", [python, "-m", "mock_data.generator"], PROJECT_ROOT),
        ("Ingesting into Bronze layer...", [python, "-m", "dlt_pipeline.pipeline"], PROJECT_ROOT),
        ("Running dbt transformations...", [python, "-m", "dbt.cli.main", "build", "--profiles-dir", "."], PROJECT_ROOT / "dbt_project"),
    ]

    try:
        for msg, cmd, cwd in steps:
            st.sidebar.info(msg)
            result = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, timeout=300
            )
            # Check for real errors (ignore exit code since stderr JSON logs cause false failures)
            combined = result.stdout + result.stderr
            has_real_error = (
                result.returncode != 0
                or "ModuleNotFoundError" in combined
                or "ImportError" in combined
                or ("Traceback" in combined and "File \"<frozen runpy>\"" in combined)
            )
            if has_real_error:
                st.sidebar.error(f"Failed: {combined[-300:]}")
                return False

        # Anomaly detection (optional)
        st.sidebar.info("Running anomaly detection...")
        subprocess.run([python, "-m", "ml_detection.train"], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120)
        subprocess.run([python, "-m", "ml_detection.predict"], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120)

    except subprocess.TimeoutExpired:
        st.sidebar.error("Pipeline step timed out")
        return False
    except Exception as e:
        st.sidebar.error(f"Error: {e}")
        return False

    return True


def load_data():
    """Load all data from DuckDB (no caching — always fresh)."""
    conn = duckdb.connect(DB_PATH, read_only=True)
    try:
        kpi = conn.execute("SELECT * FROM security_silver.kpi_summary").fetchdf()
        attacks_by_day = conn.execute("SELECT * FROM security_silver.attack_volume_by_day ORDER BY event_date").fetchdf()
        attacks_by_country = conn.execute("SELECT * FROM security_silver.attack_volume_by_country ORDER BY attack_count DESC LIMIT 10").fetchdf()
        events = conn.execute("""
            SELECT event_type, severity, country, hour_of_day, is_attack_event, is_business_hours
            FROM security_silver.silver_events
        """).fetchdf()

        # Try to load anomaly results
        try:
            anomalies = conn.execute("SELECT * FROM security_gold.anomaly_results ORDER BY window_start").fetchdf()
        except Exception:
            anomalies = pd.DataFrame()

        return kpi, attacks_by_day, attacks_by_country, events, anomalies
    finally:
        conn.close()


# Sidebar controls
st.sidebar.title(" Controls")

# Check if running locally (pipeline tools available)
_is_local = (PROJECT_ROOT / "dlt_pipeline").exists() and (PROJECT_ROOT / "dbt_project").exists()

if _is_local:
    if st.sidebar.button(" Regenerate Data", help="Re-runs the full pipeline with new random data"):
        with st.spinner("Running pipeline... this may take a minute"):
            success = run_pipeline()
            if success:
                st.sidebar.success("Pipeline complete! Data refreshed.")
                st.rerun()

if st.sidebar.button(" Refresh Dashboard", help="Reload data from database"):
    st.rerun()

st.sidebar.markdown("---")
if _is_local:
    st.sidebar.caption("Click **Regenerate Data** to generate fresh random events and update all KPIs.")
else:
    st.sidebar.caption("Dashboard running in read-only mode with pre-computed data.")

# Load data (always fresh, no cache)
kpi, attacks_by_day, attacks_by_country, events, anomalies = load_data()

# Title
st.title(" Security Incident Analytics Platform")
st.markdown("Real-time security posture monitoring with AI-powered anomaly detection")
st.divider()

# KPI Cards
st.subheader("Key Performance Indicators")
col1, col2, col3, col4, col5 = st.columns(5)

if not kpi.empty:
    row = kpi.iloc[0]
    col1.metric("Total Attacks", f"{int(row['total_attacks']):,}")
    col2.metric("Failed Login Rate", f"{row['failed_login_rate']:.1%}")
    col3.metric("Avg MTTD", f"{row['avg_mttd_minutes']:.1f} min")
    col4.metric("Avg MTTR", f"{row['avg_mttr_minutes']:.1f} min")
    col5.metric("SLA Compliance", f"{row['sla_compliance']:.1%}")

st.divider()

# Attack Volume by Day
st.subheader(" Attack Volume Over Time")
if not attacks_by_day.empty:
    fig_timeline = px.line(
        attacks_by_day,
        x="event_date",
        y="attack_count",
        title="Daily Attack Count",
        labels={"event_date": "Date", "attack_count": "Attacks"},
    )
    fig_timeline.update_layout(height=350)
    st.plotly_chart(fig_timeline, use_container_width=True)

# Two columns: Events by Type + Severity Distribution
col_left, col_right = st.columns(2)

with col_left:
    st.subheader(" Events by Type")
    type_counts = events["event_type"].value_counts().reset_index()
    type_counts.columns = ["event_type", "count"]
    fig_types = px.bar(
        type_counts,
        x="event_type",
        y="count",
        color="event_type",
        title="Event Count by Type",
    )
    fig_types.update_layout(showlegend=False, height=350)
    st.plotly_chart(fig_types, use_container_width=True)

with col_right:
    st.subheader(" Severity Distribution")
    severity_counts = events["severity"].value_counts().reset_index()
    severity_counts.columns = ["severity", "count"]
    color_map = {"low": "#4CAF50", "medium": "#FFC107", "high": "#FF9800", "critical": "#F44336"}
    fig_severity = px.pie(
        severity_counts,
        values="count",
        names="severity",
        title="Severity Breakdown",
        color="severity",
        color_discrete_map=color_map,
        hole=0.4,
    )
    fig_severity.update_layout(height=350)
    st.plotly_chart(fig_severity, use_container_width=True)

# Attack Volume by Country
st.subheader(" Top 10 Attack Source Countries")
if not attacks_by_country.empty:
    fig_country = px.bar(
        attacks_by_country,
        x="attack_count",
        y="country",
        orientation="h",
        title="Attacks by Country",
        color="attack_count",
        color_continuous_scale="Reds",
    )
    fig_country.update_layout(height=350, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_country, use_container_width=True)

# Anomaly Detection Results
st.subheader(" Anomaly Detection Timeline")
if not anomalies.empty:
    fig_anomaly = go.Figure()
    fig_anomaly.add_trace(go.Scatter(
        x=anomalies["window_start"],
        y=anomalies["anomaly_score"],
        mode="lines+markers",
        name="Anomaly Score",
        marker=dict(
            color=anomalies["anomaly_score"].apply(
                lambda s: "red" if s < -0.5 else "blue"
            ),
            size=5,
        ),
    ))
    # Threshold line
    fig_anomaly.add_hline(
        y=-0.5, line_dash="dash", line_color="red",
        annotation_text="Threshold (-0.5)",
    )
    fig_anomaly.update_layout(
        title="Anomaly Score Over Time (below -0.5 = anomalous)",
        xaxis_title="Time Window",
        yaxis_title="Anomaly Score",
        height=400,
    )
    st.plotly_chart(fig_anomaly, use_container_width=True)

    # Anomaly summary
    n_anomalies = anomalies["is_anomaly"].sum()
    st.info(f" **{n_anomalies} anomalous time windows detected** out of {len(anomalies)} total windows")
else:
    st.warning("No anomaly results found. Run `python -m ml_detection.train` and `python -m ml_detection.predict` first.")

# Hourly Activity Pattern
st.subheader(" Hourly Activity Pattern")
hourly = events["hour_of_day"].value_counts().sort_index().reset_index()
hourly.columns = ["hour", "count"]
fig_hourly = px.bar(
    hourly, x="hour", y="count",
    title="Events by Hour of Day (UTC)",
    labels={"hour": "Hour (UTC)", "count": "Event Count"},
)
fig_hourly.update_layout(height=300)
st.plotly_chart(fig_hourly, use_container_width=True)

# Footer
st.divider()
st.caption("AI-Powered Security Incident Analytics Platform | Data from DuckDB | Anomaly Detection via IsolationForest")
