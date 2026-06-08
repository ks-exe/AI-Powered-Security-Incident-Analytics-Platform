cube(`KpiSummary`, {
  sql: `SELECT * FROM security_silver.kpi_summary`,

  measures: {
    totalAttacks: { sql: `total_attacks`, type: `number` },
    failedLoginRate: { sql: `failed_login_rate`, type: `number` },
    avgMttdMinutes: { sql: `avg_mttd_minutes`, type: `number` },
    avgMttrMinutes: { sql: `avg_mttr_minutes`, type: `number` },
    slaCompliance: { sql: `sla_compliance`, type: `number` },
  },

  dimensions: {
    computedAt: { sql: `computed_at`, type: `time` },
  },
});
