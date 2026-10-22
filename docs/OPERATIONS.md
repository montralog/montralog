# Operations

## Boundary

One trusted organization per deployment. Local Docker retains SQLite and its
existing volumes. SQLite WAL must not use NFS/shared storage or multiple replicas.
The Helm production profile uses external PostgreSQL and replicated gateways.
See KUBERNETES.md and STORAGE.md. Compose uses two Gunicorn workers, four threads each.

Gateway/OTLP ports publish to loopback. Remote collection requires your controlled
HTTPS reverse proxy or VPN. Apply body limits, timeouts, connection/rate limits and
network boundaries. Keep gateway auth enabled behind identity proxies.
Do not expose Prometheus, Alertmanager or exporters publicly. TLS is not bundled.

## Credentials

Setup creates .env exclusively, with distinct random read/ingest tokens. Unix mode
0600 is requested; on Windows restrict the file ACL. Privileged Docker operators
can inspect environment variables. Secret-manager integration is future work.
Rotate by updating .env, recreating gateway/collector and updating agents.
No overlap window or per-agent credential is provided. Helm references existing
Secrets and does not generate/store token values in release history.

Browser sign-in uses expiring HttpOnly session cookies. See ACCOUNTS.md for account creation, password recovery and remote HTTPS configuration.

## Hosts, Docker and Kubernetes

Install pinned psutil on the monitored machine. Set MONTRALOG_URL and
MONTRALOG_INGEST_TOKEN; optionally set MONTRALOG_ENVIRONMENT, MONTRALOG_HOST and
MONTRALOG_INTERVAL. Run agents/host/agent.py under a restricted supervised account.
It samples its current machine/namespace, primary filesystem and aggregate network.
Network counters are cumulative. Failed intervals are not buffered. A normal
containerized agent does not automatically measure the physical host.

Add existing node-exporter, cAdvisor or kube-state-metrics endpoints to
deploy/docker/prometheus.yml. Restrict exporter access and test on your actual hosts.
No Docker socket mount is needed by this stack. Docker Desktop accounting differs
from Linux. A Helm chart is included, but automatic Kubernetes discovery,
cluster-wide RBAC installation and pod-log tailing are not. Existing cluster
collectors can forward over protected routes.

## Applications/logs

Configure SDK OTLP endpoints to the collector and use the ingest bearer token.
Applications must be instrumented; automatic arbitrary-app detection is not present.
Use OTLP logging or direct JSON ingestion. Native file tailing and multiline
parsing are not included. An existing collector can tail files and forward OTLP.
Sanitize at source: built-in redaction is partial.

Collector resource-to-metric conversion can increase cardinality. Do not use
request/user/session IDs in resource attributes. Metric names must match dashboard
queries; SDK convention changes can require query adjustments.

## Retention and capacity

SQLite RETENTION_DAYS defaults to 7 and runs hourly. Prometheus retention is
independently 7 days / 5 GB. SQLite deleted pages are reused but the file does not
automatically shrink. Schedule compaction during downtime if needed.
Monitor disk/WAL growth, query latency, collector drops/retries and backup age
independently. There is no hard SQLite disk quota or measured capacity guarantee.

## Consistent SQLite backup

Use a new destination filename:

    docker compose exec gateway python manage.py backup --destination /data/backup-2026-10-22.db
    docker compose cp gateway:/data/backup-2026-10-22.db ./backup-2026-10-22.db

Backups contain telemetry and need encryption/access controls. Copying the live raw
database file without WAL handling is not a consistent backup procedure.

Restore: stop ingestion at sources, stop collector/gateway/retention, preserve the
old volume as rollback, and restore the backup as montralog.db in a new volume
owned by uid/gid 10001. Do not carry old -wal/-shm files beside it. Point services
to the restored volume, restart, run smoke verification, inspect historical records
and resume sources. Rehearse and record recovery time.

This backs up SQLite only. Prometheus needs a separately rehearsed backup (such
as stopped-volume snapshots). Back up Alertmanager state, configuration, rules
and credentials separately. Do not expose unauthenticated admin APIs for convenience.

## Runbooks

- 401: verify role/token and recreate containers after rotation.
- 503: inspect disk capacity, writable-volume ownership, WAL and database locks.
- Empty metrics: inspect targets, collector and actual SDK metric names.
- Missing logs: check filters, source clock, auth, body size and exporter retries.
  Missing telemetry must never be interpreted as healthy.
- Missing alerts: configure a receiver and test firing/resolution. Default delivery
  sends no messages.
- Collector restart: log/trace queues use persistent storage in Docker and Helm.
  Exhaustion/disk loss can still lose records; retries may duplicate logs.
  Metric exporter state remains in memory.
- Retention errors: inspect worker logs and disk growth; age limits stop being
  enforced while the worker is down.

## Stop/upgrades

    docker compose down

Preserves named volumes. The -v option permanently removes them; do not use it
unless you intend to delete telemetry. Before an upgrade, back up all state,
test a copy, read release notes and rehearse rollback. Ordered initial migrations
are included. Database rollback is separate from image/Helm rollback.

The base image and backend images are pinned to resolved immutable digests.
Python direct dependencies are version-pinned without artifact hashes. Generate
an SBOM and scan exact images/dependencies before publishing a stable tag.
