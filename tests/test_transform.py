from types import SimpleNamespace

from geodrops_sync.transform import (
    QCN_OPTIONS, MOISTURE_STATE_OPTIONS,
    qcn_to_state, qcn_to_icon,
    moisture_index_to_state, moisture_index_to_icon,
    classify_staleness, reading_from_row, all_training,
)


def test_qcn_maps():
    assert qcn_to_state(2) == "Good"
    assert qcn_to_state(-1) == "Training"
    assert qcn_to_state(99) == "Unknown"
    assert qcn_to_icon(0) == "mdi:close-circle"
    assert set(["Bad", "Poor", "Good", "Training", "Unknown"]) == set(QCN_OPTIONS)


def test_moisture_index_maps():
    assert moisture_index_to_state(5) == "Wet+"
    assert moisture_index_to_state(0) == "Dry"
    assert moisture_index_to_state(-1) == "Unknown"
    assert moisture_index_to_icon(5) == "mdi:water"
    assert "Wet+" in MOISTURE_STATE_OPTIONS and "Dry" in MOISTURE_STATE_OPTIONS


def test_classify_staleness():
    assert classify_staleness(3, 6, 12) == "ok"
    assert classify_staleness(6, 6, 12) == "ok"      # boundary: > warn, not >=
    assert classify_staleness(7, 6, 12) == "warn"
    assert classify_staleness(12, 6, 12) == "warn"   # boundary: > skip, not >=
    assert classify_staleness(13, 6, 12) == "skip"


def test_reading_from_row_defaults():
    row = SimpleNamespace(deviceId=1001)  # everything else missing
    r = reading_from_row(row)
    assert r.device_id == 1001
    assert r.qcn_d1 == -1 and r.qcn_d2 == -1 and r.qcn_d3 == -1
    assert r.moisture_index == -1
    assert r.sync_delay_hours == 0
    assert r.moisture_pct == 0


def test_reading_from_row_values():
    row = SimpleNamespace(
        deviceId=1, miscSensorSyncDelayHour=4, moistureIndex=3, moisturePct=22.5,
        moisturePctDepth1=20, moisturePctDepth2=25, moisturePctDepth3=30,
        temperatureCSurface=18.1, temperatureCDepth1=17, temperatureCDepth2=16,
        temperatureCDepth3=15, miscBattPercent=88.7, avg7dSunExposureHourPerDay=6.2,
        qcnDepth1=2, qcnDepth2=1, qcnDepth3=0,
    )
    r = reading_from_row(row)
    assert r.moisture_pct == 22.5 and r.battery_pct == 88.7
    assert r.qcn_d1 == 2 and r.qcn_d2 == 1 and r.qcn_d3 == 0
    assert not all_training(r)


def test_all_training():
    row = SimpleNamespace(deviceId=1, qcnDepth1=-1, qcnDepth2=-1, qcnDepth3=-1)
    assert all_training(reading_from_row(row)) is True
