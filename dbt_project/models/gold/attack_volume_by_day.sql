{{ config(materialized='table') }}

SELECT
    CAST(event_time AS DATE) AS event_date,
    COUNT(*) AS attack_count,
    SUM(COUNT(*)) OVER (ORDER BY CAST(event_time AS DATE)) AS cumulative_attack_count
FROM {{ ref('silver_events') }}
WHERE is_attack_event = TRUE
GROUP BY CAST(event_time AS DATE)
ORDER BY event_date
