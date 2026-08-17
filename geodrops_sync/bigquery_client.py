"""BigQuery reader. Heavy client imported lazily so unit tests stay dependency-free."""
from __future__ import annotations

from typing import List, Sequence

from .config import BigQueryConfig, Config, DeviceConfig

_COLUMNS = """
      deviceId,
      mfgSn,
      date,
      moistureIndex,
      moisturePct,
      moisturePctDepth1,
      moisturePctDepth2,
      moisturePctDepth3,
      temperatureCSurface,
      temperatureCDepth1,
      temperatureCDepth2,
      temperatureCDepth3,
      weatherPrecipMmHr,
      miscSensorSyncDelayHour,
      miscBattPercent,
      miscIsBattPoorQuality,
      avg7dSunExposureHourPerDay,
      qcnDepth1,
      qcnDepth2,
      qcnDepth3""".rstrip()


def build_query(bq: BigQueryConfig, devices: Sequence[DeviceConfig]) -> str:
    ids = ", ".join(str(d.device_id) for d in devices)
    return (
        f"SELECT{_COLUMNS}\n"
        f"    FROM `{bq.table}`\n"
        f"    WHERE deviceId IN ({ids})\n"
        f"      AND createdAtOrigin > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), "
        f"INTERVAL {bq.lookback_hours} HOUR)\n"
        f"    QUALIFY ROW_NUMBER() OVER (PARTITION BY deviceId ORDER BY date DESC) = 1"
    )


def make_client(config: Config):
    from google.cloud import bigquery
    from google.oauth2 import service_account

    credentials = service_account.Credentials.from_service_account_file(
        config.service_account_file
    )
    return bigquery.Client(credentials=credentials, project=config.gcp.project_id)


def fetch_rows(config: Config, client) -> List:
    sql = build_query(config.bigquery, config.devices)
    return list(client.query(sql))
