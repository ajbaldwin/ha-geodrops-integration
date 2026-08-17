import json

from geodrops_sync.config import DeviceConfig, MqttConfig, SyncConfig
from geodrops_sync.transform import DeviceReading
from geodrops_sync.discovery import build_device_messages

MQTT = MqttConfig(host="h", discovery_prefix="homeassistant", topic_prefix="geodrops")
SYNC = SyncConfig(expire_after_minutes=45)
DEVICE = DeviceConfig(device_id=1001, mfg_sn="AAA111", name="zone_a")


def _reading(**over):
    base = dict(
        device_id=1001, sync_delay_hours=3, moisture_index=3, moisture_pct=22.5,
        moisture_d1=20, moisture_d2=25, moisture_d3=30, temp_surface=18, temp_d1=17,
        temp_d2=16, temp_d3=15, battery_pct=88.7, sun_7d=6.2, qcn_d1=2, qcn_d2=1, qcn_d3=0,
    )
    base.update(over)
    return DeviceReading(**base)


def _by_topic(msgs):
    return {m["topic"]: m for m in msgs}


def test_config_count_and_layout():
    configs, _ = build_device_messages(DEVICE, _reading(), SYNC, MQTT)
    assert len(configs) == 15
    topics = _by_topic(configs)
    assert "homeassistant/sensor/zone_a_moisture/config" in topics
    payload = json.loads(topics["homeassistant/sensor/zone_a_moisture/config"]["payload"])
    assert payload["state_topic"] == "geodrops/zone_a/moisture"
    assert payload["unique_id"] == "AAA111_moisture"
    assert payload["device"]["identifiers"] == ["AAA111"]
    assert payload["device"]["name"] == "Zone A Moisture Sensor"
    assert payload["expire_after"] == 2700
    assert configs[0]["retain"] is True and configs[0]["qos"] == 1


def test_enum_icons_reflect_reading():
    configs, _ = build_device_messages(DEVICE, _reading(qcn_d1=0), SYNC, MQTT)
    topics = _by_topic(configs)
    q1 = json.loads(topics["homeassistant/sensor/zone_a_qcn_d1/config"]["payload"])
    assert q1["icon"] == "mdi:close-circle"
    assert q1["options"] == ["Bad", "Poor", "Good", "Training", "Unknown"]


def test_states_full_when_not_training():
    _, states = build_device_messages(DEVICE, _reading(), SYNC, MQTT)
    topics = _by_topic(states)
    assert len(states) == 15
    assert topics["geodrops/zone_a/moisture"]["payload"] == "22.5"
    assert topics["geodrops/zone_a/moisture_state"]["payload"] == "Moist+"
    assert topics["geodrops/zone_a/battery"]["payload"] == "89"   # int(round(88.7))
    assert topics["geodrops/zone_a/qcn_d1"]["payload"] == "Good"
    assert states[0]["retain"] is True and states[0]["qos"] == 0


def test_states_suppress_moisture_when_all_training():
    _, states = build_device_messages(
        DEVICE, _reading(qcn_d1=-1, qcn_d2=-1, qcn_d3=-1), SYNC, MQTT
    )
    topics = _by_topic(states)
    assert "geodrops/zone_a/moisture" not in topics
    assert "geodrops/zone_a/moisture_d1" not in topics
    assert "geodrops/zone_a/battery" in topics       # telemetry still present
    assert "geodrops/zone_a/qcn_d1" in topics
    assert len(states) == 10
