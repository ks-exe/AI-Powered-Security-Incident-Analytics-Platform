{{ config(materialized='table') }}

SELECT
    COUNT(*) FILTER (WHERE is_attack_event) AS total_attacks,
    
    CAST(COUNT(*) FILTER (WHERE event_type = 'failed_login') AS FLOAT) /
    NULLIF(COUNT(*) FILTER (WHERE event_type IN ('failed_login', 'successful_login')), 0)
        AS failed_login_rate,
    
    AVG(EXTRACT(EPOCH FROM (detection_time - event_time)) / 60.0)
    FILTER (WHERE detection_time IS NOT NULL)
        AS avg_mttd_minutes,
    
    AVG(EXTRACT(EPOCH FROM (resolution_time - detection_time)) / 60.0)
    FILTER (WHERE resolution_time IS NOT NULL)
        AS avg_mttr_minutes,
    
    CAST(COUNT(*) FILTER (
        WHERE resolution_time IS NOT NULL 
        AND EXTRACT(EPOCH FROM (resolution_time - detection_time)) / 60.0 <= 240
    ) AS FLOAT) /
    NULLIF(COUNT(*) FILTER (WHERE resolution_time IS NOT NULL), 0)
        AS sla_compliance,
    
    CURRENT_TIMESTAMP AS computed_at

FROM {{ ref('silver_events') }}
