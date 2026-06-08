{% macro is_rfc1918(column_name) %}
    (
        -- 10.0.0.0/8
        split_part({{ column_name }}, '.', 1)::INT = 10
        OR
        -- 172.16.0.0/12 (172.16.x.x to 172.31.x.x)
        (split_part({{ column_name }}, '.', 1)::INT = 172
         AND split_part({{ column_name }}, '.', 2)::INT BETWEEN 16 AND 31)
        OR
        -- 192.168.0.0/16
        (split_part({{ column_name }}, '.', 1)::INT = 192
         AND split_part({{ column_name }}, '.', 2)::INT = 168)
    )
{% endmacro %}
