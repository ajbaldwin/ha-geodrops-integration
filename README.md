# ha-geodrops-integration

Sync GeoDrops soil-moisture sensor readings from BigQuery to Home Assistant over MQTT.

GeoDrops sensors report into a Google BigQuery dataset. This service polls that
dataset on a schedule, transforms each device's latest reading, and republishes it
to an MQTT broker using Home Assistant MQTT Discovery — so each sensor shows up in
Home Assistant as a device with its own entities, with no Home Assistant-specific
code or coupling anywhere in this service. It runs standalone: as a Docker
container, a systemd service, a cron job, or under AppDaemon.

## Architecture

```
GeoDrops → BigQuery ─▶ [ha-geodrops-integration] ─▶ MQTT broker ─▶ Home Assistant
                        fetch → transform → publish        (MQTT Discovery consumer)
```

## Requirements

- A Google Cloud project with BigQuery access to the GeoDrops public dataset
  (`geodrops-prod.db_public`) — see [`docs/setup-bigquery.md`](docs/setup-bigquery.md).
- An MQTT broker reachable from wherever this service runs.
- Home Assistant with the MQTT integration and discovery enabled — see
  [`docs/setup-mqtt-ha.md`](docs/setup-mqtt-ha.md).

## Quickstart

### Run directly

```bash
pip install .
cp examples/config.example.yaml config.yaml
# edit config.yaml: gcp.project_id, mqtt.host/username, your devices

export GEODROPS_MQTT_PASSWORD=your-mqtt-password
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

geodrops-sync --once          # one sync cycle, then exit
geodrops-sync                 # daemon: loops every sync.interval_minutes
```

### Run with Docker Compose

```bash
cp examples/config.example.yaml config.yaml
# edit config.yaml as above, then place your service-account key at
# ./service-account.json (both are gitignored / bind-mounted read-only)

cat > .env <<'EOF'
GEODROPS_MQTT_PASSWORD=your-mqtt-password
EOF

docker compose up -d
```

`docker-compose.yml` mounts `config.yaml` and `service-account.json` read-only into
the container and sets `GOOGLE_APPLICATION_CREDENTIALS` for you; only
`GEODROPS_MQTT_PASSWORD` needs to come from `.env`.

## Config reference

All keys live in `config.yaml` (copy from `examples/config.example.yaml`). Two
secrets are never read from the file — only from the environment.

| Key | Default | Meaning |
|---|---|---|
| `gcp.project_id` | *(required)* | GCP project the BigQuery client bills/runs queries under. Queries run against this project but read the GeoDrops **public** dataset. |
| `bigquery.table` | `geodrops-prod.db_public.p_sensor_unified` | Fully-qualified BigQuery table to read. Override if GeoDrops renames the dataset/table. |
| `bigquery.lookback_hours` | `12` | How far back to look for each device's latest row. |
| `mqtt.host` | *(required)* | MQTT broker hostname/IP. |
| `mqtt.port` | `1883` | MQTT broker port. |
| `mqtt.username` | `""` | MQTT username. If set, `GEODROPS_MQTT_PASSWORD` must also be set. |
| `mqtt.discovery_prefix` | `homeassistant` | Must match Home Assistant's MQTT integration discovery prefix. |
| `mqtt.topic_prefix` | `geodrops` | Prefix for state topics (`{topic_prefix}/{device.name}/{field}`). |
| `sync.interval_minutes` | `15` | Daemon loop interval between sync cycles. |
| `sync.expire_after_minutes` | `45` | HA `expire_after` on each discovered entity — how long after the last publish HA marks it unavailable. |
| `sync.staleness_warn_hours` | `6` | Above this sync delay, publish the reading but log a warning. |
| `sync.staleness_skip_hours` | `12` | Above this sync delay, skip the device entirely for this cycle (logged as an error). |
| `devices` | *(required, non-empty)* | List of `{ device_id, mfg_sn, name }`. See [`docs/finding-device-ids.md`](docs/finding-device-ids.md). |

**Secret environment variables (not in `config.yaml`):**

| Variable | Meaning |
|---|---|
| `GEODROPS_MQTT_PASSWORD` | MQTT broker password. Required if `mqtt.username` is set. |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to the GCP service-account JSON key. Required — the BigQuery client reads it directly. |

## Run modes

- `geodrops-sync --once` — run a single sync cycle and exit (non-zero on fatal
  error). Use this for cron, systemd timers, or an AppDaemon `run_every` job.
- `geodrops-sync` (default) — self-scheduling daemon: loops every
  `sync.interval_minutes`, logs and retries on a per-cycle failure instead of
  crashing, and shuts down cleanly on SIGINT/SIGTERM.
- `--config PATH` — path to the config file (default `config.yaml`).
- `--log-level LEVEL` — `DEBUG`, `INFO` (default), `WARNING`, or `ERROR`.

## Data freshness

GeoDrops readings are typically **3–6 hours old** by the time they land in
BigQuery, on top of whatever polling delay this service's `interval_minutes`
adds. This is fine for tracking soil-moisture trends, but it is **not suitable
as a real-time signal for irrigation cutoffs** or any decision that needs
current-moment moisture data.

## Documentation

- [Setting up BigQuery access](docs/setup-bigquery.md)
- [Setting up MQTT and Home Assistant discovery](docs/setup-mqtt-ha.md)
- [Finding your device IDs](docs/finding-device-ids.md)
- [Troubleshooting](docs/troubleshooting.md)

## Attribution

This project originates from the
[GeoDrops community forum thread on integrating GeoDrops sensors with Home Assistant](https://geodrops.discourse.group/t/integrating-geodrops-soil-moisture-sensors-with-home-assistant/280),
where Adam Baldwin (Scythe) first published the BigQuery-to-MQTT approach this
service is built from. Forum user rokhead's AppDaemon-based post (#15) explored a
different, non-blocking way to schedule the sync and informed this project's
decision to run fully standalone rather than as a `shell_command` inside Home
Assistant.

GeoDrops is an independent product; this project is not affiliated with or
endorsed by GeoDrops.

## License

MIT — see [`LICENSE`](LICENSE).
