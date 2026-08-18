"""Build Home Assistant MQTT Discovery config messages and state messages."""
from __future__ import annotations

import json

from .config import DeviceConfig, MqttConfig, SyncConfig
from .transform import (
    DeviceReading, all_training,
    qcn_to_state, qcn_to_icon,
    moisture_index_to_state, moisture_index_to_icon,
    QCN_OPTIONS, MOISTURE_STATE_OPTIONS,
)


def _device_block(device: DeviceConfig) -> dict:
    friendly = device.name.replace("_", " ").title()
    return {
        "identifiers": [device.mfg_sn],
        "name": f"{friendly} Moisture Sensor",
        "manufacturer": "GeoDrops",
        "model": "Soil Moisture Sensor",
        "sw_version": "A2.02r1",
    }


def _config_msg(mqtt_cfg, sync_cfg, device, device_block, suffix, fields) -> dict:
    payload = {
        "state_topic": f"{mqtt_cfg.topic_prefix}/{device.name}/{suffix}",
        "unique_id": f"{device.mfg_sn}_{suffix}",
        "device": device_block,
        "expire_after": sync_cfg.expire_after_minutes * 60,
    }
    payload.update(fields)
    return {
        "topic": f"{mqtt_cfg.discovery_prefix}/sensor/{device.name}_{suffix}/config",
        "payload": json.dumps(payload),
        "retain": True,
        "qos": 1,
    }


def _state_msg(mqtt_cfg, device, suffix, value) -> dict:
    return {
        "topic": f"{mqtt_cfg.topic_prefix}/{device.name}/{suffix}",
        "payload": str(value),
        "retain": True,
        "qos": 0,
    }


def _discovery_configs(device, reading, sync_cfg, mqtt_cfg) -> list[dict]:
    device_block = _device_block(device)

    def cfg(suffix, fields):
        return _config_msg(mqtt_cfg, sync_cfg, device, device_block, suffix, fields)

    moisture = {"unit_of_measurement": "%", "device_class": "moisture", "state_class": "measurement"}
    temp = {"unit_of_measurement": "°C", "device_class": "temperature", "state_class": "measurement"}
    return [
        cfg("moisture", {"name": "Dominant Moisture", **moisture}),
        cfg("moisture_state", {
            "name": "Moisture State", "device_class": "enum",
            "options": MOISTURE_STATE_OPTIONS, "icon": moisture_index_to_icon(reading.moisture_index),
        }),
        cfg("moisture_d1", {"name": "Moisture Depth 1", **moisture}),
        cfg("moisture_d2", {"name": "Moisture Depth 2", **moisture}),
        cfg("moisture_d3", {"name": "Moisture Depth 3", **moisture}),
        cfg("qcn_d1", {"name": "Quality Depth 1", "device_class": "enum",
                       "options": QCN_OPTIONS, "icon": qcn_to_icon(reading.qcn_d1)}),
        cfg("qcn_d2", {"name": "Quality Depth 2", "device_class": "enum",
                       "options": QCN_OPTIONS, "icon": qcn_to_icon(reading.qcn_d2)}),
        cfg("qcn_d3", {"name": "Quality Depth 3", "device_class": "enum",
                       "options": QCN_OPTIONS, "icon": qcn_to_icon(reading.qcn_d3)}),
        cfg("battery", {"name": "Battery", "unit_of_measurement": "%",
                        "device_class": "battery", "state_class": "measurement"}),
        cfg("sync_delay", {"name": "Sync Delay", "unit_of_measurement": "h",
                           "state_class": "measurement"}),
        cfg("temp_surface", {"name": "Surface Temperature", **temp}),
        cfg("temp_d1", {"name": "Temperature Depth 1", **temp}),
        cfg("temp_d2", {"name": "Temperature Depth 2", **temp}),
        cfg("temp_d3", {"name": "Temperature Depth 3", **temp}),
        cfg("sun_7d", {"name": "Avg. 7-Day Sun", "unit_of_measurement": "h",
                       "icon": "mdi:white-balance-sunny"}),
    ]


def _state_messages(device, reading, mqtt_cfg) -> list[dict]:
    def st(suffix, value):
        return _state_msg(mqtt_cfg, device, suffix, value)

    telemetry = [
        st("qcn_d1", qcn_to_state(reading.qcn_d1)),
        st("qcn_d2", qcn_to_state(reading.qcn_d2)),
        st("qcn_d3", qcn_to_state(reading.qcn_d3)),
        st("battery", int(round(reading.battery_pct))),
        st("sync_delay", reading.sync_delay_hours),
        st("temp_surface", reading.temp_surface),
        st("temp_d1", reading.temp_d1),
        st("temp_d2", reading.temp_d2),
        st("temp_d3", reading.temp_d3),
        st("sun_7d", reading.sun_7d),
    ]
    if all_training(reading):
        return telemetry
    moisture = [
        st("moisture", reading.moisture_pct),
        st("moisture_state", moisture_index_to_state(reading.moisture_index)),
        st("moisture_d1", reading.moisture_d1),
        st("moisture_d2", reading.moisture_d2),
        st("moisture_d3", reading.moisture_d3),
    ]
    return moisture + telemetry


def build_device_messages(
    device: DeviceConfig, reading: DeviceReading, sync_cfg: SyncConfig, mqtt_cfg: MqttConfig
) -> tuple[list[dict], list[dict]]:
    return _discovery_configs(device, reading, sync_cfg, mqtt_cfg), \
        _state_messages(device, reading, mqtt_cfg)
