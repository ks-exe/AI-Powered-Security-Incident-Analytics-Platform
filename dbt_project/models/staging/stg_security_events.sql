{{ config(materialized='view') }}

SELECT
    event_id,
    event_time,
    username,
    src_ip,
    destination_ip,
    hostname,
    event_type,
    severity,
    status,
    country,
    operating_system,
    department,
    detection_time,
    resolution_time,
    _ingested_at,
    _source_file,
    _batch_id
FROM {{ source('bronze', 'security_events_resource') }}
