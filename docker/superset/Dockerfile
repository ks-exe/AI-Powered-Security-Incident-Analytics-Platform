FROM apache/superset:3.1.0

USER root

# Install additional DB drivers if needed
RUN pip install duckdb-engine

# Copy initialization script and make it executable
COPY init_superset.sh /app/init_superset.sh
RUN chmod +x /app/init_superset.sh

USER superset

COPY superset_config.py /app/pythonpath/superset_config.py

EXPOSE 8088

# NOTE: Run the init script manually after container start:
#   docker exec -it security_superset /app/init_superset.sh
# Or override the entrypoint to run it once on first start.
