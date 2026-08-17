# Setting up MQTT and Home Assistant discovery

This service publishes to plain MQTT topics plus Home Assistant MQTT Discovery
config topics. It has no direct dependency on Home Assistant — anything that
speaks MQTT Discovery will pick up the entities — but this doc assumes Home
Assistant as the consumer.

## 1. An MQTT broker

You need an MQTT broker reachable from wherever this service runs (same host,
same network, or a route to it). [Mosquitto](https://mosquitto.org/) is the
common choice and is also what the Home Assistant "Mosquitto broker" add-on runs.

If you're already running the Home Assistant MQTT integration, you likely have a
broker already — reuse it.

## 2. A broker user for this service

Create (or reuse) an MQTT user on the broker, then set:

```yaml
mqtt:
  host: 127.0.0.1        # broker address reachable from this service
  port: 1883
  username: homeassistant  # must match the broker user you created
```

and export the matching password as an environment variable — **not** in
`config.yaml`:

```bash
export GEODROPS_MQTT_PASSWORD=the-broker-users-password
```

If `mqtt.username` is set but `GEODROPS_MQTT_PASSWORD` is missing from the
environment, the service fails fast at startup with a config error rather than
attempting an unauthenticated connection.

For Mosquitto specifically, adding a user is typically:

```bash
mosquitto_passwd -b /path/to/passwordfile homeassistant the-broker-users-password
```

(exact steps depend on your Mosquitto install/add-on — consult its docs.)

## 3. Enable MQTT discovery in Home Assistant

1. **Settings → Devices & Services → Add Integration → MQTT**, and point it at
   the same broker (host/port/credentials).
2. Discovery is enabled by default in the HA MQTT integration. Confirm the
   **discovery prefix** — default `homeassistant` — matches this service's
   `mqtt.discovery_prefix`:

   ```yaml
   mqtt:
     discovery_prefix: homeassistant   # must match HA's MQTT integration config
   ```

   If you changed HA's discovery prefix from the default, update this value to
   match, or entities will never show up.

## 4. Run a sync cycle and confirm entities appear

```bash
geodrops-sync --once
```

Then in Home Assistant:

1. **Settings → Devices & Services → Devices**.
2. You should see one device per entry in `config.yaml`'s `devices` list, named
   `"{Friendly Name} Moisture Sensor"` (derived from `name`, e.g. `zone_a` →
   "Zone A Moisture Sensor").
3. Each device groups a set of entities: Dominant Moisture, Moisture State,
   Moisture Depth 1–3, Quality Depth 1–3, Battery, Sync Delay, Surface/Depth
   Temperatures, and Avg. 7-Day Sun. (Moisture entities are withheld — not
   created with a value — while a sensor is still in "Training"; see
   [`docs/troubleshooting.md`](troubleshooting.md).)

If the devices don't appear, check
[`docs/troubleshooting.md`](troubleshooting.md#entities-missing-in-home-assistant).

## 5. Retained discovery and entity expiry

Discovery config messages are published with `retain: true`, so Home Assistant
(or any client that (re)connects later) picks up the entity definitions even if
it wasn't listening at publish time — you don't need to keep this service
running continuously for HA to already know about the entities from the last
cycle.

Each entity is also configured with an MQTT `expire_after` equal to
`sync.expire_after_minutes * 60` seconds (default 45 minutes). If this service
stops publishing for longer than that — daemon down, cron stopped, network
issue — Home Assistant will mark those entities **unavailable** rather than
showing a stale last value. This is expected behavior, not a bug: it's the
signal that sync has stopped, not that the sensor itself is offline.
