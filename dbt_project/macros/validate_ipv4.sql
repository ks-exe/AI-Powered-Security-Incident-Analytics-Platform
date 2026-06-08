{% macro validate_ipv4(column_name) %}
    {{ column_name }} IS NOT NULL
    AND regexp_matches({{ column_name }}, '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
{% endmacro %}
