cube(`SecurityEvents`, {
  sql: `SELECT * FROM security_silver.silver_events`,

  measures: {
    count: { type: `count` },
    attackCount: {
      type: `count`,
      filters: [{ sql: `${CUBE}.is_attack_event = TRUE` }],
    },
    failedLoginCount: {
      type: `count`,
      filters: [{ sql: `${CUBE}.event_type = 'failed_login'` }],
    },
    uniqueIps: { sql: `src_ip`, type: `countDistinct` },
    uniqueUsers: { sql: `username`, type: `countDistinct` },
  },

  preAggregations: {
    daily: {
      measures: [count, attackCount, failedLoginCount, uniqueIps, uniqueUsers],
      timeDimension: eventTime,
      granularity: `day`,
      partitionGranularity: `month`,
    },
  },

  dimensions: {
    eventId: { sql: `event_id`, type: `string`, primaryKey: true },
    eventTime: { sql: `event_time`, type: `time` },
    username: { sql: `username`, type: `string` },
    srcIp: { sql: `src_ip`, type: `string` },
    destinationIp: { sql: `destination_ip`, type: `string` },
    hostname: { sql: `hostname`, type: `string` },
    eventType: { sql: `event_type`, type: `string` },
    severity: { sql: `severity`, type: `string` },
    severityRank: { sql: `severity_rank`, type: `number` },
    status: { sql: `status`, type: `string` },
    country: { sql: `country`, type: `string` },
    operatingSystem: { sql: `operating_system`, type: `string` },
    department: { sql: `department`, type: `string` },
    hourOfDay: { sql: `hour_of_day`, type: `number` },
    dayOfWeek: { sql: `day_of_week`, type: `number` },
    isBusinessHours: { sql: `is_business_hours`, type: `boolean` },
    isInternalIp: { sql: `is_internal_ip`, type: `boolean` },
    isAttackEvent: { sql: `is_attack_event`, type: `boolean` },
  },
});
