# Troubleshooting

## No results for a device / empty sync cycle

**Symptom:** A device configured in `devices` never gets a reading published, or
logs show it being skipped.

**Cause:** One of:
- The physical sensor hasn't reported recently — its latest row is older than
  `bigquery.lookback_hours` (default 12h), so the query's
  `createdAtOrigin > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL lookback_hours HOUR)`
  filter excludes it.
- The device's sync delay (`miscSensorSyncDelayHour`) exceeds
  `sync.staleness_skip_hours` (default 12h) — the service deliberately skips
  publishing for that device this cycle and logs an **ERROR**.
- The `device_id` in `config.yaml` doesn't match the sensor (see
  [`docs/finding-device-ids.md`](finding-device-ids.md)) — the query filters on
  exactly the configured `device_id`s, so a wrong ID silently returns nothing for
  that entry.

**Fix:**
- Increase `bigquery.lookback_hours` temporarily to confirm whether the device
  has *any* recent row at all.
- Check the sensor is physically online and has connectivity to report to
  GeoDrops in the first place — this service can't fix an offline sensor.
- Re-verify `device_id` / `mfg_sn` against the portal or a scratch query.
- Run with `--log-level DEBUG` to see per-device staleness classification.

## BigQuery schema drift (columns renamed/changed)

**Symptom:** Queries start failing with "column not found" / "unrecognized
column" errors, or previously-working fields come back empty/`None`.

**Cause:** GeoDrops has changed the underlying BigQuery table's column names or
structure before (see spec background). The dataset/table itself may also move.

**Fix:**
- If the *table* moved (dataset/table name changed), update `bigquery.table` in
  `config.yaml` — no code change needed.
- If *column names* changed, the fixed column list lives in one place:
  `_COLUMNS` in `geodrops_sync/bigquery_client.py`. Update the `SELECT` list
  there to match the new schema.
- The row → `DeviceReading` mapping (which column feeds which field, and default
  handling for missing/`None` values) is in `reading_from_row()` in
  `geodrops_sync/transform.py`. If a field is renamed rather than removed,
  update the corresponding `getattr(row, "old_name")` call there too.
- After either change, re-run the test suite (`pytest`) — `test_transform.py`
  and `test_discovery.py` cover the mapping and payload shape and will catch
  most mismatches.

## BigQuery access denied / permission error

**Symptom:** Queries fail immediately with `accessDenied`, `403`, or a "user does
not have permission" / "Permission bigquery.jobs.create denied" error.

**Cause:** One of two independent things (see
[`docs/setup-bigquery.md`](setup-bigquery.md)):
- **`bigquery.jobs.create` denied** → your service account is missing the
  **BigQuery Job User** role on *your own* project (`gcp.project_id`). This is the
  one role you must grant; queries run and bill in your project.
- **Read denied on `geodrops-prod.db_public`** → this is a GeoDrops-side grant, not
  yours. The dataset is normally publicly readable, so a Job-User service account
  can read it with no dataset grant. If read specifically is denied, GeoDrops has
  changed how the dataset is shared — adding roles on *your* project cannot fix it.

**Fix:**
- Confirm the service account has **BigQuery Job User** on the project named in
  `gcp.project_id`, and that `gcp.project_id` is *your* project, not `geodrops-prod`.
- Confirm the BigQuery API is enabled on your project.
- If only the data read is denied (job creation works), check the
  [GeoDrops forum thread](https://geodrops.discourse.group/t/integrating-geodrops-soil-moisture-sensors-with-home-assistant/280)
  for the current public-sharing status before touching your own IAM.

## MQTT authentication failure

**Symptom:** Publish fails with an authentication/connection error; nothing
appears in Home Assistant.

**Cause:** `mqtt.username` in `config.yaml` doesn't match a valid broker user, or
`GEODROPS_MQTT_PASSWORD` is wrong, unset, or not exported in the environment the
service actually runs in (a shell export in one terminal doesn't carry into a
different terminal, a systemd unit, or a Docker container unless passed
explicitly).

**Fix:**
- Confirm `GEODROPS_MQTT_PASSWORD` is set in the exact environment the process
  runs in — for Docker Compose, check it's present in `.env` (referenced as
  `${GEODROPS_MQTT_PASSWORD:?set in .env}` in `docker-compose.yml`, which fails
  the container fast if missing).
- If `mqtt.username` is set but the password env var is missing entirely,
  `config.py` raises a `ConfigError` at startup — check the logged error message,
  it names the missing variable.
- Test the broker credentials independently with `mosquitto_pub`/`mosquitto_sub`
  before assuming the bug is in this service.

## Entities missing in Home Assistant

**Symptom:** The service runs and logs successful publishes, but no device/
entities appear in HA.

**Cause:** Almost always `mqtt.discovery_prefix` doesn't match the discovery
prefix Home Assistant's MQTT integration is configured with (default
`homeassistant` on both sides, but either can be customized independently).

**Fix:**
- In Home Assistant, check **Settings → Devices & Services → MQTT → Configure**
  for the configured discovery prefix.
- Confirm `mqtt.discovery_prefix` in `config.yaml` matches exactly.
- Use an MQTT client (e.g. `mosquitto_sub -t 'homeassistant/sensor/#' -v`) to
  confirm discovery config messages are actually being published and retained
  under the prefix you expect.
- Also confirm the service and Home Assistant are pointed at the *same* broker —
  a `mqtt.host` mismatch produces the same symptom (successful publish, nothing
  in HA) if there are two brokers in play.

## Everything shows "Unknown" / no moisture reading

**Symptom:** A device's Moisture, Moisture State, and Moisture Depth 1–3
entities are missing or show no value, while Battery, Sync Delay, Quality
Depth 1–3, and temperature entities are present and updating normally.

**Cause:** This is expected behavior, not a fault. When all three quality codes
(`qcnDepth1/2/3`) read `-1` ("Training"), the sensor is still in its initial
training/calibration period and hasn't produced a trustworthy moisture reading
yet. The service deliberately suppresses the moisture-related state topics in
this case (`all_training()` in `geodrops_sync/transform.py`) while still
publishing all discovery configs and the non-moisture telemetry, so the device
stays visible in HA and you can see it's alive and training rather than assuming
it's broken.

**Fix:** None needed — this resolves on its own once the sensor finishes
training and starts reporting real QCN values. Check the "Quality Depth 1/2/3"
entities; once any of them move off "Training", moisture values should start
appearing on the next cycle.
