cube(`AnomalyResults`, {
  sql: `SELECT * FROM security_silver.anomaly_results`,

  measures: {
    count: { type: `count` },
    anomalyScore: { sql: `anomaly_score`, type: `avg` },
    anomalyCount: {
      type: `count`,
      filters: [{ sql: `${CUBE}.is_anomaly = TRUE` }],
    },
    totalEventCount: { sql: `total_event_count`, type: `sum` },
  },

  dimensions: {
    windowStart: { sql: `window_start`, type: `time`, primaryKey: true },
    windowEnd: { sql: `window_end`, type: `time` },
    isAnomaly: { sql: `is_anomaly`, type: `boolean` },
    topContributingFeature: { sql: `top_contributing_feature`, type: `string` },
    modelVersion: { sql: `model_version`, type: `string` },
  },
});
