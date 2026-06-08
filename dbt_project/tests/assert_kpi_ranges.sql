-- Validate that rate KPIs are between 0.0 and 1.0
SELECT *
FROM {{ ref('kpi_summary') }}
WHERE failed_login_rate < 0.0 OR failed_login_rate > 1.0
   OR (sla_compliance IS NOT NULL AND (sla_compliance < 0.0 OR sla_compliance > 1.0))
