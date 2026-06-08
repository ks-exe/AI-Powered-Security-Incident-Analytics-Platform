{{
    config(
        materialized='incremental',
        unique_key='event_id'
    )
}}

WITH deduplicated AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY event_id 
            ORDER BY _ingested_at DESC
        ) AS row_num
    FROM {{ source('bronze', 'security_events_resource') }}
    {% if is_incremental() %}
    WHERE _ingested_at > (SELECT MAX(_ingested_at) FROM {{ this }})
    {% endif %}
),

validated AS (
    SELECT * FROM deduplicated
    WHERE row_num = 1
      AND TRY_CAST(event_time AS TIMESTAMP) IS NOT NULL
      AND {{ validate_ipv4('src_ip') }}
      AND severity IN ('low', 'medium', 'high', 'critical')
)

SELECT
    event_id,
    CAST(event_time AS TIMESTAMP) AS event_time,
    detection_time,
    resolution_time,
    LOWER(username) AS username,
    src_ip,
    destination_ip,
    UPPER(hostname) AS hostname,
    event_type,
    LOWER(severity) AS severity,
    {{ severity_rank('severity') }} AS severity_rank,
    status,
    country,
    operating_system,
    department,
    EXTRACT(HOUR FROM CAST(event_time AS TIMESTAMP)) AS hour_of_day,
    EXTRACT(ISODOW FROM CAST(event_time AS TIMESTAMP)) AS day_of_week,
    CASE WHEN EXTRACT(HOUR FROM CAST(event_time AS TIMESTAMP)) BETWEEN 9 AND 16 
         THEN TRUE ELSE FALSE END AS is_business_hours,
    {{ is_rfc1918('src_ip') }} AS is_internal_ip,
    CASE WHEN event_type IN (
        'malware_alert','privilege_escalation',
        'suspicious_ip_activity','brute_force_attempt'
    ) THEN TRUE ELSE FALSE END AS is_attack_event,
    _ingested_at,
    _source_file,
    _batch_id
FROM validated
