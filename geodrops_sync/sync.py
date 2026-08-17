"""One sync cycle: fetch rows -> transform -> build messages -> publish."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from .config import Config
from .transform import reading_from_row, classify_staleness
from .discovery import build_device_messages
from .bigquery_client import fetch_rows
from .publisher import publish_messages

_log = logging.getLogger("geodrops_sync")


@dataclass
class SyncSummary:
    devices: int
    configs: int
    states: int
    skipped: int


def run_once(config: Config, *, rows=None, fetch=fetch_rows,
             publish=publish_messages, client=None, logger=None) -> SyncSummary:
    log = logger or _log
    if rows is None:
        rows = fetch(config, client)
    log.info("Query returned %d results", len(rows))

    by_id = {d.device_id: d for d in config.devices}
    messages = []
    devices = configs = states = skipped = 0

    for row in rows:
        device = by_id.get(row.deviceId)
        if device is None:
            log.warning("Unknown deviceId %s, skipping", row.deviceId)
            continue
        reading = reading_from_row(row)
        state = classify_staleness(
            reading.sync_delay_hours,
            config.sync.staleness_warn_hours,
            config.sync.staleness_skip_hours,
        )
        if state == "skip":
            log.error("%s (%s) very stale (%sh) - SKIPPING",
                      device.name, device.mfg_sn, reading.sync_delay_hours)
            skipped += 1
            continue
        if state == "warn":
            log.warning("%s (%s) stale (%sh) - publishing anyway",
                        device.name, device.mfg_sn, reading.sync_delay_hours)
        else:
            log.info("%s (%s) sync delay %sh",
                     device.name, device.mfg_sn, reading.sync_delay_hours)

        dev_configs, dev_states = build_device_messages(
            device, reading, config.sync, config.mqtt
        )
        messages.extend(dev_configs)
        messages.extend(dev_states)
        devices += 1
        configs += len(dev_configs)
        states += len(dev_states)

    if messages:
        publish(messages, config.mqtt)
        log.info("Published %d retained discovery configs and %d retained states",
                 configs, states)
    else:
        log.info("No messages to publish")

    return SyncSummary(devices=devices, configs=configs, states=states, skipped=skipped)
