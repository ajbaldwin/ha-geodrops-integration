"""Standalone GeoDrops BigQuery -> MQTT (Home Assistant Discovery) sync service."""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ha-geodrops-integration")
except PackageNotFoundError:  # running from a source checkout, not pip-installed
    __version__ = "0.0.0+source"
