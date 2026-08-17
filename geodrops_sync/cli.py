"""Command-line entry point: one-shot (--once) or self-scheduling daemon."""
from __future__ import annotations

import argparse
import logging
import signal
import time

from .config import load_config
from .sync import run_once

_log = logging.getLogger("geodrops_sync")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="geodrops-sync",
                                description="Sync GeoDrops sensors from BigQuery to MQTT.")
    p.add_argument("--once", action="store_true",
                   help="Run one sync cycle and exit (for cron/systemd/AppDaemon).")
    p.add_argument("--config", default="config.yaml", help="Path to config.yaml.")
    p.add_argument("--log-level", default="INFO",
                   help="Logging level (DEBUG, INFO, WARNING, ERROR).")
    return p


def _install_signal_stop():
    state = {"run": True}

    def stop(signum, frame):
        _log.info("Received signal %s, shutting down after current cycle", signum)
        state["run"] = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    return lambda: state["run"]


def run_daemon(config, *, run=run_once, sleep=time.sleep, should_continue=None) -> int:
    if should_continue is None:
        should_continue = _install_signal_stop()
    interval_seconds = config.sync.interval_minutes * 60
    while should_continue():
        try:
            run(config)
        except Exception:  # noqa: BLE001 - a bad cycle must not kill the daemon
            _log.exception("Sync cycle failed; will retry next interval")
        if should_continue():
            sleep(interval_seconds)
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="[%(asctime)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        config = load_config(args.config)
    except Exception as exc:  # noqa: BLE001 - config errors are fatal, report cleanly
        _log.error("Failed to load config from %s: %s", args.config, exc)
        return 1

    if args.once:
        try:
            run_once(config)
            return 0
        except Exception:  # noqa: BLE001
            _log.exception("Sync failed")
            return 1
    return run_daemon(config)


if __name__ == "__main__":
    raise SystemExit(main())
