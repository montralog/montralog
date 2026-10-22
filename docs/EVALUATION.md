# Test Montralog

Follow the Docker installation in the root README. Use a fresh folder and its generated credentials. Never copy somebody else's `.env` or database into a shared release.

1. Run `python scripts/check_install.py`. It checks readiness, authenticated telemetry access, anonymous access rejection and Prometheus connectivity without changing data.
2. Optionally run `python scripts/check_install.py --demo`. This explicitly inserts synthetic demo logs, traces and a deployment event.
3. Sign in, open Connect data, test the bundled Prometheus connection, and save your own connection if needed. Docker's bundled endpoint is `http://prometheus:9090` with no authentication.
4. Explore demo logs, patterns and traces. Instrument a real application using the API guide to test your own traffic.
5. Create a dashboard with a graph, stat and two timeline panels. Save, reload and edit it; sign out and back in to verify persistence.
6. Create a short-lived read API token, use it to read telemetry, revoke it and verify access stops. Keep its value private.
7. Add an alert rule and check its state and in-app notifications. Slack needs your own private webhook and a real delivery test; it is optional.
8. Restart the stack and confirm dashboards, accounts and source settings remain available.

For real Windows/Docker resource measurements use the optional local metrics agent. It runs under your local account and needs manual startup after reboot; it is not a Windows service.

Report your OS, Docker/Compose versions, steps, expected and actual results, and timestamps. Sanitize screenshots and logs. Never include passwords, tokens, webhook URLs or private telemetry.

`docker compose stop` stops services while keeping data. `docker compose down` also preserves named volumes. Do not use `down -v` with valuable data. Back up before upgrades; restoring a backup is the rollback path, rather than running an older binary against a newer schema.
