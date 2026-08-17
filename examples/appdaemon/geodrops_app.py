"""AppDaemon app: run the geodrops-integration core once per interval.

Requires the `ha-geodrops-integration` package importable in AppDaemon's
environment (add it to the AppDaemon add-on's `python_packages`, or pip install
it into the AppDaemon venv). Secrets come from the AppDaemon process environment:
GEODROPS_MQTT_PASSWORD and GOOGLE_APPLICATION_CREDENTIALS.
"""
import appdaemon.plugins.hass.hassapi as hass

from geodrops_sync.bigquery_client import make_client
from geodrops_sync.config import load_config
from geodrops_sync.sync import run_once


class GeodropsSync(hass.Hass):
    def initialize(self):
        self.cfg = load_config(self.args["config_path"])
        try:
            self.client = make_client(self.cfg)
        except Exception as exc:  # noqa: BLE001 - can't run without a client
            self.error(f"geodrops sync: failed to create BigQuery client: {exc}")
            return
        minutes = int(self.args.get("interval_minutes", 15))
        self.run_every(self.sync, "now", minutes * 60)

    def sync(self, kwargs):
        try:
            summary = run_once(self.cfg, client=self.client)
            self.log(f"geodrops sync: {summary}")
        except Exception as exc:  # noqa: BLE001
            self.error(f"geodrops sync failed: {exc}")
