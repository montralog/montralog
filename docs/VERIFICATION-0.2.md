# Verification — 0.2.0-rc1, 2026-10-22

## Application and packaging

- 35 tests pass: SQLite and real PostgreSQL gateway behavior, authorization,
  validation/atomicity, redaction, search, pagination, OTLP JSON, span deduplication,
  concurrency, retention, legacy schema adoption, parallel startup and rejection
  of unsupported newer schemas.
- PostgreSQL integration used an isolated PostgreSQL 17.6 database named
  montralog_test, not the running local telemetry database.
- SQLite snapshot import committed 1003 logs and 3 spans to an empty PostgreSQL
  test database, preserving the read-only source.
- JavaScript syntax checked.
- Installable Python wheel built with static assets, both SQL migration variants,
  license/notice and CLI entry point included.

## Helm validation

- Helm 3.19.4 obtained from its official distribution and checksum-verified.
- Strict chart lint passes.
- SQLite and PostgreSQL profiles render with 17 and 19 Kubernetes resources.
- Seven invalid/unsafe value combinations are rejected.
- Rendered configurations checked using actual Prometheus, Alertmanager and
  Collector binaries. Disk-queue validation includes its mounted storage directory.

## Real Kubernetes runtime

Tested on an isolated single-node kind cluster with Kubernetes 1.34.0.
The existing kubeconfig/context was not used for mutations.

- Chart installed; gateway, collector, Prometheus and Alertmanager became ready.
- HTTP authentication, ingestion, search, patterns and trace correlation passed.
- OTLP HTTP JSON logs/traces and a histogram metric passed through the collector,
  storage and Prometheus application dashboard query.
- SQLite gateway pod restarted; telemetry remained on the PVC.
- Chart upgraded to external PostgreSQL mode with two gateway replicas and a PDB.
- Both replicas read shared telemetry successfully.
- Rolling gateway restart completed; HTTP smoke passed again.

These tests establish functional single-node Kubernetes deployment behavior.
They do not establish multi-zone/node HA, production storage performance or
NetworkPolicy enforcement: kind's default CNI does not provide that enforcement.

## Local upgrade

The existing installation at D:\Monitoring Project was backed up and reorganized.
Existing .env and named telemetry volumes were preserved. Old source files are
under work/upgrades. A consistent pre-upgrade SQLite backup was made inside the
existing data volume before source replacement.

The 0.2 Docker image built, all long-running services started, and the one-shot
collector-volume initializer completed. Live HTTP and collector round-trip checks
passed against the upgraded local installation.

Controlled queue recovery also passed: the gateway/retention worker were stopped,
a synthetic log was accepted by the collector, the collector was restarted, and
the gateway was restored. The log subsequently reached storage from the persistent
queue. This is one recovery exercise, not an exhaustive failure/loss qualification.

## Remaining qualification

Real ingress/controller/TLS and database TLS, CNI policy enforcement, production
storage class behavior, multi-node failure recovery, database PITR/restore,
long-duration load, exact supported capacity, external alert delivery, full SDK
gRPC/protobuf matrix, real exporter/Kubernetes integrations and independent
security/dependency review remain outstanding.

Shared read/ingest tokens are not user RBAC or tenant isolation. This is a stronger
deployment candidate, not a production certification or market-preference claim.
GitHub CI is configured but has not been run remotely.
