# Historical 0.4 evaluation report

For the access and identity release, see ACCESS_VERIFICATION.md. The report below predates those changes.

# Evaluation verification — 2026-10-22

Version: 0.4.0-rc1. Platform: Windows Docker Desktop, Linux containers, Docker Engine 29.7.2.

A separate Docker Compose project used new named volumes, independently generated credentials and alternate loopback ports. Existing Montralog data was not reused.

Passed:
- Application image build from sanitized release sources.
- Fresh schema initialization and six long-running services ready.
- Gateway readiness, anonymous read rejection and authenticated reads.
- Prometheus connection with two healthy scrape targets.
- Explicit synthetic demo ingestion: 60 logs, 120 spans and one deployment event.
- HTTP smoke checks: authentication, logs, patterns and trace correlation.
- Collector accepts all three telemetry signals and rejects invalid authentication.
- Collector-to-storage and collector-to-Prometheus-to-dashboard query path.
- Fresh administrator account creation.
- Helm rendering: SQLite 17 resources, PostgreSQL 20 resources, seven invalid configurations rejected.

Earlier application verification for the same application source passed 90 tests including an isolated PostgreSQL database. This packaging pass changes documentation, startup scripts and CI configuration; it does not represent a remote CI run.

Limitations: no independent security audit, production load test, current-version target Kubernetes cluster deployment, restore rehearsal or real Slack destination delivery was completed in this packaging pass. See PRODUCTION.md before relying on this deployment.
