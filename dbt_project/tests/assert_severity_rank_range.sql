-- Test that severity_rank is between 1 and 4 for all records
SELECT *
FROM {{ ref('silver_events') }}
WHERE severity_rank < 1 OR severity_rank > 4
