cube(`AttackVolumeByDay`, {
  sql: `SELECT * FROM security_silver.attack_volume_by_day`,

  measures: {
    attackCount: { sql: `attack_count`, type: `sum` },
    cumulativeAttackCount: { sql: `cumulative_attack_count`, type: `max` },
  },

  dimensions: {
    eventDate: { sql: `event_date`, type: `time` },
  },

  preAggregations: {
    daily: {
      measures: [attackCount, cumulativeAttackCount],
      timeDimension: eventDate,
      granularity: `day`,
    },
  },
});
