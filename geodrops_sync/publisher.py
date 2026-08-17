"""MQTT publisher. paho imported lazily so unit tests stay dependency-free."""
from __future__ import annotations

from .config import MqttConfig


def publish_messages(messages: list[dict], mqtt_cfg: MqttConfig, publish_multiple=None) -> None:
    if not messages:
        return
    if publish_multiple is None:
        import paho.mqtt.publish as publish
        publish_multiple = publish.multiple
    auth = None
    if mqtt_cfg.username:
        auth = {"username": mqtt_cfg.username, "password": mqtt_cfg.password}
    publish_multiple(messages, hostname=mqtt_cfg.host, port=mqtt_cfg.port, auth=auth)
