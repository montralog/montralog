# Connection manager verification — 22 October 2026

Version 0.4.0-rc1. All 90 automated tests passed with no skips against SQLite
and a disposable PostgreSQL 17.6 database. Coverage includes earlier telemetry,
dashboard, account, notification and token behavior, plus source administration,
CSRF, credential masking/preservation, default-source resolution, explicit panel
source validation, failed-save rejection, blocked metadata destinations and safe
connection errors. Backend authentication headers were verified with a mocked
HTTP transport; no third-party credentials were supplied.

Live local verification:

- Existing Docker deployment upgraded to schema 4 with prior accounts, saved
  dashboards and telemetry preserved. A SQLite snapshot was made first at
  /data/pre-connections-20261022.db inside the existing data volume.
- Browser source catalog and guided Prometheus form opened successfully.
- Use local Docker Prometheus populated the server URL and connection name.
- Test connection returned two scrape-status series without authentication.
- Save & test stored Local Prometheus as the workspace default.
- A live CPU metric query used Local Prometheus and returned a series.
- Explicit datasource=builtin used Bundled Prometheus and returned a CPU series.
- Application gateway remained healthy and all six app services remained running.

The connection test is a real Prometheus API query, not evidence that every
exporter is healthy. The source list shows the last test result; Data sources
also queries current scrape targets. External Loki/Tempo/SQL sources are not
implemented. Remote authenticated Prometheus servers require target-environment
validation. Kubernetes deployment of this version was not performed in this run.
