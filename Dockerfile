FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY geodrops_sync ./geodrops_sync
RUN pip install --no-cache-dir .

# Run as an unprivileged user. The service only reads its bind-mounted config +
# credentials (mounted read-only) and makes outbound BigQuery/MQTT connections;
# it needs no root and no write access to the image.
RUN useradd --create-home --uid 10001 appuser
USER appuser

# Default: self-scheduling daemon. Override with `--once` for cron/systemd.
ENTRYPOINT ["geodrops-sync"]
CMD ["--config", "/config/config.yaml"]
