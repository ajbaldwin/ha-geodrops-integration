# Finding your device IDs

Each entry under `devices` in `config.yaml` needs three values:

```yaml
devices:
  - { device_id: 1001, mfg_sn: "AAA111", name: zone_a }
```

- `device_id` — the numeric GeoDrops device ID (BigQuery column `deviceId`).
- `mfg_sn` — the manufacturer serial number (BigQuery column `mfgSn`). This is
  used as the Home Assistant device's unique `identifiers` value, so it must be
  correct and stable per physical sensor.
- `name` — a name you choose. Used to build MQTT topics
  (`{topic_prefix}/{name}/*`) and, combined with each metric suffix, entity
  unique IDs. Keep it **lowercase, underscore-separated, and stable** — changing
  it later effectively creates new entities in Home Assistant rather than
  renaming the existing ones.

## Option A: GeoDrops portal

Check the GeoDrops web portal / app for your account — each registered sensor's
device ID and serial number are typically shown on its device detail page.
Cross-reference the serial number printed on the physical sensor if you have
multiple.

## Option B: Scratch query against BigQuery

If you already have BigQuery access set up (see
[`docs/setup-bigquery.md`](setup-bigquery.md)), you can query the same public
dataset this service reads to list the devices reporting under your account:

```sql
SELECT DISTINCT deviceId, mfgSn
FROM `geodrops-prod.db_public.p_sensor_unified`
WHERE mfgSn IN ('AAA111', 'AAA222')   -- serials you know from the sensor labels
ORDER BY deviceId;
```

If you don't already know any serial numbers to filter on, you'll need another
way to scope the query to your account's devices specifically — the raw table
has no account/owner column exposed for arbitrary filtering, so pulling a full
unfiltered device list this way isn't practical. Use the portal (Option A) to
get your first serial number(s), or narrow by a `date` range you know your
sensors reported in, then cross-check the results against your own hardware.

## Choosing `name`

`name` becomes part of:
- MQTT state topics: `{topic_prefix}/{name}/moisture`, `.../battery`, etc.
- Discovery config topics: `{discovery_prefix}/sensor/{name}_{suffix}/config`
- The Home Assistant device's friendly name: `name.replace("_", " ").title()` +
  " Moisture Sensor" (e.g. `zone_a` → "Zone A Moisture Sensor").

Pick something location-based and stable (`zone_a`, `back_garden_bed`)
rather than anything tied to the serial number or a value that might change —
renaming it later means Home Assistant treats it as a brand-new device rather
than updating the existing one.
