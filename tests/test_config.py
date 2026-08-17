import pytest

from geodrops_sync.config import parse_config, ConfigError

BASE_RAW = {
    "gcp": {"project_id": "proj"},
    "mqtt": {"host": "10.0.0.1", "username": "homeassistant"},
    "devices": [
        {"device_id": 1001, "mfg_sn": "AAA111", "name": "zone_a"},
    ],
}
ENV = {"GEODROPS_MQTT_PASSWORD": "pw", "GOOGLE_APPLICATION_CREDENTIALS": "/creds.json"}


def test_defaults_applied():
    cfg = parse_config(BASE_RAW, ENV)
    assert cfg.bigquery.table == "geodrops-prod.db_public.p_sensor_unified"
    assert cfg.bigquery.lookback_hours == 12
    assert cfg.mqtt.port == 1883
    assert cfg.mqtt.discovery_prefix == "homeassistant"
    assert cfg.mqtt.topic_prefix == "geodrops"
    assert cfg.sync.interval_minutes == 15
    assert cfg.sync.expire_after_minutes == 45
    assert cfg.sync.staleness_warn_hours == 6
    assert cfg.sync.staleness_skip_hours == 12


def test_secrets_come_from_env():
    cfg = parse_config(BASE_RAW, ENV)
    assert cfg.mqtt.password == "pw"
    assert cfg.service_account_file == "/creds.json"


def test_devices_parsed_as_tuple():
    cfg = parse_config(BASE_RAW, ENV)
    assert cfg.devices[0].device_id == 1001
    assert cfg.devices[0].mfg_sn == "AAA111"
    assert cfg.devices[0].name == "zone_a"


def test_missing_project_id_raises():
    raw = {**BASE_RAW, "gcp": {"project_id": ""}}
    with pytest.raises(ConfigError, match="project_id"):
        parse_config(raw, ENV)


def test_no_devices_raises():
    raw = {**BASE_RAW, "devices": []}
    with pytest.raises(ConfigError, match="devices"):
        parse_config(raw, ENV)


def test_missing_mqtt_password_with_username_raises():
    with pytest.raises(ConfigError, match="GEODROPS_MQTT_PASSWORD"):
        parse_config(BASE_RAW, {"GOOGLE_APPLICATION_CREDENTIALS": "/creds.json"})


def test_missing_credentials_env_raises():
    with pytest.raises(ConfigError, match="GOOGLE_APPLICATION_CREDENTIALS"):
        parse_config(BASE_RAW, {"GEODROPS_MQTT_PASSWORD": "pw"})


def test_missing_mqtt_host():
    raw = {**BASE_RAW, "mqtt": {**BASE_RAW["mqtt"], "host": ""}}
    with pytest.raises(ConfigError, match="mqtt.host"):
        parse_config(raw, ENV)
