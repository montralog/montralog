# Verification — 0.3.0-rc1, 22 October 2026

70 automated tests passed with no skips against SQLite and an isolated
PostgreSQL 17.6 database. Coverage includes earlier telemetry behavior,
authentication, migrations, session revocation, dashboard ownership/editing,
panel validation, administrator restrictions, managed token scope/expiry/revocation,
Slack URL validation, hidden webhook secrets, delivery retries, deduplicated
firing transitions, missing-data UNKNOWN state and literal log-count conditions.
Slack delivery in unit tests uses a mocked sender; it is not external delivery proof.

Helm render/security checks passed for SQLite (17 resources), PostgreSQL
(20 resources including the single notification worker), and seven rejected
invalid configurations. The 0.3 chart was not installed in a Kubernetes cluster
during this update. Target-cluster validation remains necessary.

Live local Docker checks passed:

- Existing telemetry/account/dashboard data preserved through schema migration 3.
- Requested admin/admin123 account login works without a browser read token.
- Mixed dashboard saved with graph/statistic panels, log/deployment timelines,
  message-pattern bars and recorded traces.
- Managed read token reads telemetry and cannot ingest; ingest token writes logs.
- Managed ingest token forwards OTLP metrics through the gateway to the collector.
- Revoked read token is rejected on the next request.
- Notification worker heartbeat appears; an explicitly labelled synthetic
  log-count rule generated a real in-app inbox entry.
- Temporary verification rule was removed and verification tokens revoked.
- Existing local Docker and Windows collection resumed after Docker startup repair.

Browser checks passed for the new login, dashboard library/editor, adding a bar
panel, saving the edited dashboard, real metric previews, multiple timeline
panels, notification configuration/inbox and token controls.

No Slack webhook was supplied. Slack is ready to configure but external Slack
delivery has not been verified and no external message was sent.

Before migration, the local SQLite snapshot was saved inside the existing volume
as /data/pre-studio-20261022.db. Source rollback files are under work/upgrades.
Docker Desktop initially crashed on stale AF_UNIX runtime endpoints; only runtime
socket directories were moved to timestamped backups. Container images and data
volumes were preserved. See Docker's upstream issue tracker for the matching
[runtime endpoint failure](https://github.com/docker/desktop-feedback/issues/554).

This remains a release candidate, without a production availability/capacity
guarantee, independent security review, SSO or tenant isolation. Workspace alert
routes and Prometheus/Alertmanager routes are separate, as described in STUDIO.md.
