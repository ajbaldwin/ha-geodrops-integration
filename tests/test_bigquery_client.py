from geodrops_sync.config import BigQueryConfig, DeviceConfig
from geodrops_sync.bigquery_client import build_query, fetch_rows

DEVICES = [
    DeviceConfig(1001, "AAA111", "zone_a"),
    DeviceConfig(1002, "AAA222", "zone_b"),
]


def test_build_query_contains_table_devices_and_window():
    sql = build_query(BigQueryConfig(table="ds.tbl", lookback_hours=12), DEVICES)
    assert "FROM `ds.tbl`" in sql
    assert "1001" in sql and "1002" in sql
    assert "INTERVAL 12 HOUR" in sql
    assert "QUALIFY ROW_NUMBER() OVER (PARTITION BY deviceId ORDER BY date DESC) = 1" in sql
    assert "moisturePctDepth3" in sql and "qcnDepth3" in sql


class _FakeClient:
    def __init__(self, rows):
        self.rows = rows
        self.sql = None

    def query(self, sql):
        self.sql = sql
        return iter(self.rows)


def test_fetch_rows_uses_client_and_returns_list():
    from geodrops_sync.config import Config, GcpConfig, MqttConfig, SyncConfig
    cfg = Config(
        gcp=GcpConfig("p"), bigquery=BigQueryConfig(table="ds.tbl"),
        mqtt=MqttConfig(host="h"), sync=SyncConfig(),
        devices=tuple(DEVICES), service_account_file="/c.json",
    )
    client = _FakeClient(["r1", "r2"])
    rows = fetch_rows(cfg, client)
    assert rows == ["r1", "r2"]
    assert "FROM `ds.tbl`" in client.sql
