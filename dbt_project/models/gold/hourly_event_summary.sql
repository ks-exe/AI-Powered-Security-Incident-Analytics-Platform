{{ config(materialized='table') }}

SELECT
    DATE_TRUNC('hour', event_time) AS event_hour,
    event_type,
    COUNT(*) AS event_count,
    COUNT(DISTINCT src_ip) AS unique_ips,
    COUNT(DISTINCT username) AS unique_users
FROM {{ ref('silver_events') }}
GROUP BY DATE_TRUNC('hour', event_time), event_type
ORDER BY event_hour, event_type
