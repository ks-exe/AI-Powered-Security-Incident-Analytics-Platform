{{ config(materialized='table') }}

SELECT
    country,
    COUNT(*) AS attack_count,
    CAST(COUNT(*) AS FLOAT) / NULLIF(SUM(COUNT(*)) OVER (), 0) AS percentage_of_total
FROM {{ ref('silver_events') }}
WHERE is_attack_event = TRUE
GROUP BY country
ORDER BY attack_count DESC
