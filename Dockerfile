FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY geodrops_sync ./geodrops_sync
RUN pip install --no-cache-dir .

# Default: self-scheduling daemon. Override with `--once` for cron/systemd.
ENTRYPOINT ["geodrops-sync"]
CMD ["--config", "/config/config.yaml"]
