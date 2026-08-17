from geodrops_sync.config import MqttConfig
from geodrops_sync.publisher import publish_messages


def test_publish_passes_messages_host_port_and_auth():
    calls = {}

    def fake_multiple(messages, hostname, port, auth):
        calls["messages"] = messages
        calls["hostname"] = hostname
        calls["port"] = port
        calls["auth"] = auth

    msgs = [{"topic": "t", "payload": "1", "retain": True, "qos": 0}]
    cfg = MqttConfig(host="10.0.0.1", port=1883, username="u", password="pw")
    publish_messages(msgs, cfg, publish_multiple=fake_multiple)

    assert calls["messages"] is msgs
    assert calls["hostname"] == "10.0.0.1" and calls["port"] == 1883
    assert calls["auth"] == {"username": "u", "password": "pw"}


def test_publish_omits_auth_when_no_username():
    calls = {}

    def fake_multiple(messages, hostname, port, auth):
        calls["auth"] = auth

    cfg = MqttConfig(host="h", username="", password="")
    publish_messages([{"topic": "t", "payload": "1", "retain": True, "qos": 0}],
                     cfg, publish_multiple=fake_multiple)
    assert calls["auth"] is None


def test_publish_noop_on_empty():
    called = {"n": 0}

    def fake_multiple(*a, **k):
        called["n"] += 1

    publish_messages([], MqttConfig(host="h"), publish_multiple=fake_multiple)
    assert called["n"] == 0
