"""Config model and loader. Pure Python; secrets injected from env."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Tuple

import yaml


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""


@dataclass(frozen=True)
class DeviceConfig:
    device_id: int
    mfg_sn: str
    name: str


@dataclass(frozen=True)
class GcpConfig:
    project_id: str


@dataclass(frozen=True)
class BigQueryConfig:
    table: str = "geodrops-prod.db_public.p_sensor_unified"
    lookback_hours: int = 12


@dataclass(frozen=True)
class MqttConfig:
    host: str = ""
    port: int = 1883
    username: str = ""
    password: str = ""
    discovery_prefix: str = "homeassistant"
    topic_prefix: str = "geodrops"


@dataclass(frozen=True)
class SyncConfig:
    interval_minutes: int = 15
    expire_after_minutes: int = 45
    staleness_warn_hours: int = 6
    staleness_skip_hours: int = 12


@dataclass(frozen=True)
class Config:
    gcp: GcpConfig
    bigquery: BigQueryConfig
    mqtt: MqttConfig
    sync: SyncConfig
    devices: Tuple[DeviceConfig, ...]
    service_account_file: str


def _int(value, key: str) -> int:
    """Coerce a config value to int, raising ConfigError that names the key on failure."""
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{key} must be an integer, got {value!r}") from exc


def parse_config(raw: dict, env: Mapping[str, str]) -> Config:
    raw = raw or {}

    project_id = ((raw.get("gcp") or {}).get("project_id") or "").strip()
    if not project_id:
        raise ConfigError("gcp.project_id is required and must be non-empty")

    bq_raw = raw.get("bigquery") or {}
    bigquery = BigQueryConfig(
        table=bq_raw.get("table", BigQueryConfig().table),
        lookback_hours=_int(bq_raw.get("lookback_hours", BigQueryConfig().lookback_hours),
                            "bigquery.lookback_hours"),
    )

    mqtt_raw = raw.get("mqtt") or {}
    host = (mqtt_raw.get("host") or "").strip()
    if not host:
        raise ConfigError("mqtt.host is required and must be non-empty")
    username = mqtt_raw.get("username", "")
    password = env.get("GEODROPS_MQTT_PASSWORD", "")
    if username and not password:
        raise ConfigError(
            "mqtt.username is set but GEODROPS_MQTT_PASSWORD is not in the environment"
        )
    mqtt = MqttConfig(
        host=host,
        port=_int(mqtt_raw.get("port", MqttConfig().port), "mqtt.port"),
        username=username,
        password=password,
        discovery_prefix=mqtt_raw.get("discovery_prefix", MqttConfig().discovery_prefix),
        topic_prefix=mqtt_raw.get("topic_prefix", MqttConfig().topic_prefix),
    )

    sync_raw = raw.get("sync") or {}
    sync = SyncConfig(
        interval_minutes=_int(sync_raw.get("interval_minutes", SyncConfig().interval_minutes),
                              "sync.interval_minutes"),
        expire_after_minutes=_int(sync_raw.get("expire_after_minutes", SyncConfig().expire_after_minutes),
                                  "sync.expire_after_minutes"),
        staleness_warn_hours=_int(sync_raw.get("staleness_warn_hours", SyncConfig().staleness_warn_hours),
                                  "sync.staleness_warn_hours"),
        staleness_skip_hours=_int(sync_raw.get("staleness_skip_hours", SyncConfig().staleness_skip_hours),
                                  "sync.staleness_skip_hours"),
    )

    devices_raw = raw.get("devices") or []
    if not devices_raw:
        raise ConfigError("at least one entry under devices is required")
    devices = []
    for d in devices_raw:
        try:
            devices.append(DeviceConfig(
                device_id=int(d["device_id"]),
                mfg_sn=str(d["mfg_sn"]),
                name=str(d["name"]),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigError(f"invalid device entry {d!r}: {exc}") from exc

    service_account_file = env.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not service_account_file:
        raise ConfigError(
            "GOOGLE_APPLICATION_CREDENTIALS must be set to the service-account JSON path"
        )

    return Config(
        gcp=GcpConfig(project_id=project_id),
        bigquery=bigquery,
        mqtt=mqtt,
        sync=sync,
        devices=tuple(devices),
        service_account_file=service_account_file,
    )


def load_config(path: str, env: Mapping[str, str] = os.environ) -> Config:
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return parse_config(raw, env)
