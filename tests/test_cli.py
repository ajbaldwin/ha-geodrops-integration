import logging

from geodrops_sync.cli import build_parser, run_daemon


def test_parser_defaults_and_flags():
    p = build_parser()
    ns = p.parse_args([])
    assert ns.once is False and ns.config == "config.yaml"
    ns2 = p.parse_args(["--once", "--config", "/x.yaml", "--log-level", "DEBUG"])
    assert ns2.once is True and ns2.config == "/x.yaml" and ns2.log_level == "DEBUG"


def test_run_daemon_loops_then_stops():
    calls = {"run": 0, "sleep": []}

    def fake_run(config, client=None):
        calls["run"] += 1

    def fake_sleep(seconds):
        calls["sleep"].append(seconds)

    # stop after two iterations: while(T), run, if(T), sleep, while(T), run, if(T), sleep, while(F)
    seq = iter([True, True, True, True, False])
    rc = run_daemon(
        _FakeConfig(interval_minutes=15), run=fake_run,
        sleep=fake_sleep, should_continue=lambda: next(seq),
    )
    assert rc == 0
    assert calls["run"] == 2
    assert calls["sleep"] == [900, 900]


def test_run_daemon_survives_cycle_error():
    seq = iter([True, False, False])

    def boom(config, client=None):
        raise RuntimeError("bigquery down")

    rc = run_daemon(_FakeConfig(interval_minutes=1), run=boom,
                    sleep=lambda s: None, should_continue=lambda: next(seq))
    assert rc == 0  # error logged, loop continued, clean exit


class _FakeConfig:
    def __init__(self, interval_minutes):
        from geodrops_sync.config import SyncConfig
        self.sync = SyncConfig(interval_minutes=interval_minutes)
