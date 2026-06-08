{% macro severity_rank(column_name) %}
    CASE LOWER({{ column_name }})
        WHEN 'low' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'high' THEN 3
        WHEN 'critical' THEN 4
        ELSE 0
    END
{% endmacro %}
