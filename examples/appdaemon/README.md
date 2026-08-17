# AppDaemon Example

This directory contains an optional AppDaemon example demonstrating how to run the geodrops-integration core as a Home Assistant AppDaemon app.

## AppDaemon is Optional

The **primary** way to run geodrops-integration is via:
- **Standalone daemon mode**: Run the package directly as a long-running process.
- **Scheduled task mode** (`--once` CLI flag): Integrate with cron, systemd, or other schedulers to run once at fixed intervals.

**AppDaemon is one optional supported runner**, not a core dependency. The package does not require AppDaemon to install or function.

## How to Use

### 1. Make the Package Importable in AppDaemon

The AppDaemon environment must be able to import `geodrops_sync`. You have two options:

**Option A: Install via pip (recommended)**
```bash
pip install ha-geodrops-integration
```
Install this into the AppDaemon add-on's virtual environment or include `ha-geodrops-integration` in the add-on's `python_packages` configuration.

**Option B: Manual installation**
If running a standalone AppDaemon instance, ensure the package is installed in its environment:
```bash
python -m pip install ha-geodrops-integration
```

### 2. Configure AppDaemon

Copy `apps.yaml` and `geodrops_app.py` into your AppDaemon `config/apps/` directory:
```bash
cp apps.yaml /path/to/appdaemon/config/apps/
cp geodrops_app.py /path/to/appdaemon/config/apps/
```

Adjust the `config_path` in `apps.yaml` to point to your geodrops configuration file (e.g., `/config/geodrops/config.yaml`).

### 3. Set Environment Variables for Secrets

AppDaemon reads secrets from the process environment. The geodrops-integration core requires two environment variables:

- **`GEODROPS_MQTT_PASSWORD`**: The MQTT broker password.
- **`GOOGLE_APPLICATION_CREDENTIALS`**: Path to the Google Cloud service account JSON file, or the JSON itself (if your config uses JSON format).

Set these in your AppDaemon environment:
```bash
export GEODROPS_MQTT_PASSWORD="your_mqtt_password"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

If using the Home Assistant AppDaemon add-on, set these in the add-on's environment settings.

### 4. Run AppDaemon

AppDaemon will automatically start the `GeodropsSync` app, which:
- Loads the configuration from the path specified in `apps.yaml`.
- Runs the sync every 15 minutes (or as specified by `interval_minutes`).
- Logs each sync result to AppDaemon's log.

Adjust `interval_minutes` in `apps.yaml` to change the sync frequency.

## Architecture

The `GeodropsSync` app:
- Calls `load_config()` to read your geodrops configuration.
- Schedules `run_every()` to execute the sync at the specified interval.
- On each run, calls `run_once()` from the core package to fetch data, check staleness, build MQTT messages, and publish to your broker.
- Catches exceptions and logs errors without crashing.

## Differences from Standalone Mode

- **Scheduler**: AppDaemon handles scheduling (via `run_every`); standalone uses daemon mode or cron.
- **Logging**: AppDaemon logs to its configured output; standalone can log to stdout/files.
- **State**: AppDaemon keeps the app process alive continuously; standalone can be ephemeral.

Both modes run the same core `run_once()` function, ensuring consistent behavior.

## Troubleshooting

**"ModuleNotFoundError: No module named 'geodrops_sync'"**
- Ensure the package is installed in AppDaemon's environment.
- Verify `python_packages` in the add-on config includes `ha-geodrops-integration`.

**"geodrops sync failed: ..."**
- Check the error message in AppDaemon logs.
- Verify `GEODROPS_MQTT_PASSWORD` and `GOOGLE_APPLICATION_CREDENTIALS` are set in the environment.
- Confirm the `config_path` in `apps.yaml` is accessible.

**Sync never runs**
- Check AppDaemon is running: `docker logs appdaemon` (or equivalent for your setup).
- Verify the app is registered in `apps.yaml`.
- Look for initialization errors in the logs.
