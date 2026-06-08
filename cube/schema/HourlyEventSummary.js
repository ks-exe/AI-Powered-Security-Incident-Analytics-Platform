cube(`HourlyEventSummary`, {
  sql: `SELECT * FROM security_silver.hourly_event_summary`,

  measures: {
    eventCount: { sql: `event_count`, type: `sum` },
    uniqueIps: { sql: `unique_ips`, type: `sum` },
    uniqueUsers: { sql: `unique_users`, type: `sum` },
  },

  dimensions: {
    eventHour: { sql: `event_hour`, type: `time` },
    eventType: { sql: `event_type`, type: `string` },
  },

  preAggregations: {
    hourly: {
      measures: [eventCount, uniqueIps, uniqueUsers],
      timeDimension: eventHour,
      granularity: `hour`,
    },
  },
});
