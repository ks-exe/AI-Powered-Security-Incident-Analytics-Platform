cube(`AttackVolumeByCountry`, {
  sql: `SELECT * FROM security_silver.attack_volume_by_country`,

  measures: {
    attackCount: { sql: `attack_count`, type: `sum` },
    percentageOfTotal: { sql: `percentage_of_total`, type: `number` },
  },

  dimensions: {
    country: { sql: `country`, type: `string` },
  },
});
