from types import SimpleNamespace

from geodrops_sync.config import (
    Config, GcpConfig, BigQueryConfig, MqttConfig, SyncConfig, DeviceConfig,
)
from geodrops_sync.sync import run_once, SyncSummary


def _cfg(devices):
    return Config(
        gcp=GcpConfig("p"), bigquery=BigQueryConfig(), mqtt=MqttConfig(host="h"),
        sync=SyncConfig(), devices=tuple(devices), service_account_file="/c.json",
    )


def _row(device_id, sync_delay=3, qcn=2):
    return SimpleNamespace(
        deviceId=device_id, miscSensorSyncDelayHour=sync_delay, moistureIndex=3,
        moisturePct=20, moisturePctDepth1=20, moisturePctDepth2=20, moisturePctDepth3=20,
        temperatureCSurface=18, temperatureCDepth1=18, temperatureCDepth2=18,
        temperatureCDepth3=18, miscBattPercent=90, avg7dSunExposureHourPerDay=6,
        qcnDepth1=qcn, qcnDepth2=qcn, qcnDepth3=qcn,
    )


def test_run_once_publishes_and_summarizes():
    cfg = _cfg([DeviceConfig(1001, "AAA111", "zone_a")])
    published = {"calls": 0}

    def fake_publish(messages, mqtt_cfg):
        published["calls"] += 1
        published["messages"] = messages

    summary = run_once(cfg, rows=[_row(1001)], publish=fake_publish)
    assert isinstance(summary, SyncSummary)
    assert summary.devices == 1 and summary.skipped == 0
    assert summary.configs == 15 and summary.states == 15
    assert published["calls"] == 1              # aggregated into a single publish
    assert len(published["messages"]) == 30


def test_run_once_skips_stale_device():
    cfg = _cfg([DeviceConfig(1001, "AAA111", "zone_a")])
    published = {}
    summary = run_once(cfg, rows=[_row(1001, sync_delay=99)],
                       publish=lambda m, c: published.setdefault("m", m))
    assert summary.skipped == 1 and summary.devices == 0
    assert "m" not in published  # nothing published


def test_run_once_ignores_unknown_device_id():
    cfg = _cfg([DeviceConfig(1001, "AAA111", "zone_a")])
    summary = run_once(cfg, rows=[_row(9999)], publish=lambda m, c: None)
    assert summary.devices == 0 and summary.skipped == 0


def test_run_once_uses_injected_fetch():
    cfg = _cfg([DeviceConfig(1001, "AAA111", "zone_a")])
    summary = run_once(cfg, fetch=lambda config, client: [_row(1001)],
                       publish=lambda m, c: None)
    assert summary.devices == 1


def test_run_once_uses_default_fetch_with_real_client_seam():
    """No `rows` and no `fetch` injected: exercises the real fetch_rows ->
    client.query(sql) path that production (via cli.main) relies on."""
    cfg = _cfg([DeviceConfig(1001, "AAA111", "zone_a")])

    class FakeClient:
        def __init__(self):
            self.queries = []

        def query(self, sql):
            self.queries.append(sql)
            return [_row(1001)]

    fake_client = FakeClient()
    summary = run_once(cfg, client=fake_client, publish=lambda m, c: None)

    assert len(fake_client.queries) == 1
    assert "FROM" in fake_client.queries[0]
    assert summary.devices == 1 and summary.skipped == 0
