# Kubernetes and Helm

## Supported topologies

The chart deploys the gateway, a disk-buffered OTLP Collector and optional
Prometheus/Alertmanager StatefulSets. Databases are deliberately not bundled into
the production profile: PostgreSQL HA, backups and disaster recovery belong to
your managed database/operator.

Default evaluation profile: one SQLite gateway, PVC and retention sidecar.
Production example: two stateless PostgreSQL gateways, rolling updates, PDB,
hourly retention CronJob, TLS ingress and external database credentials.
Neither profile makes single Prometheus/Collector instances highly available.

The chart rejects SQLite with multiple replicas, ephemeral SQLite storage,
PostgreSQL without a database Secret, ingress without TLS/host and disabled
Prometheus without an external URL. Values are schema-validated.

## Prerequisites

- Kubernetes 1.27+ with a compatible CSI storage class.
- Helm 3, a reachable registry and the gateway image you built.
- Existing auth Secret; optionally PostgreSQL, TLS and alert configuration Secrets.
- For NetworkPolicy enforcement, a CNI that supports NetworkPolicy.
- Operator-tested PostgreSQL backups and restore; verify-full TLS for remote DBs.

There is no public registry image published by this project yet. Build and push
your image to your registry and set image.repository/tag/digest accordingly.

## Credentials

Create a namespace and auth Secret containing read-token and ingest-token, each
a different random value of at least 32 characters. Use a secret manager or
local protected files with kubectl create secret --from-file; do not put token
values in shell history, Helm values or Git.

For PostgreSQL, create a Secret containing database-url:

    postgresql://user:password@database.example:5432/montralog?sslmode=verify-full

Use your CA/trust configuration as appropriate. The connection string is consumed
by psycopg; configure PostgreSQL privileges, TLS, capacity and failover separately.
The initial schema owner needs DDL privileges for versioned startup migrations.
A separate migration job/limited runtime DB role is a future hardening step.

## Install

Evaluation:

    helm upgrade --install montralog deploy/helm/montralog \
      --namespace observability --create-namespace \
      --set auth.existingSecret=montralog-auth \
      --set image.repository=your-registry/montralog \
      --set image.tag=0.5.0-rc1 --wait --timeout 5m

Production example: copy values-production.yaml into an operator-controlled
configuration directory. Replace registry, host, TLS secret and database Secret
names, then:

    helm upgrade --install montralog deploy/helm/montralog \
      --namespace observability --create-namespace \
      -f your-production-values.yaml --wait --timeout 5m

For private access:

    kubectl -n observability port-forward svc/montralog 8080:8080

The resulting internal collector endpoint is montralog-collector:4317
(gRPC) / :4318 (HTTP). Applications need the ingest bearer header. Remote OTLP TLS
termination is not exposed automatically by this chart.

## Exporters

Set prometheus.extraScrapeConfigs to reach existing node-exporter, cAdvisor,
kube-state-metrics, database or queue exporters. This chart does not install
privileged agents, cluster-wide discovery/RBAC or a full kube-prometheus-stack.
Alternatively disable bundled Prometheus and provide prometheus.externalUrl.
Add networkPolicy.extraEgress rules for exporter/DB/backend ports beyond the
defaults (same-namespace traffic, DNS, PostgreSQL 5432 and Prometheus 9090).

Resource-to-metric label conversion can increase cardinality. Keep request/user IDs
out of resource labels and size storage using real workloads.

## Upgrade and rollback

Back up the database and metrics state before upgrades. SQLite must remain a
single gateway and uses Recreate; its retention container shares the same PVC.
The chart keeps the standalone SQLite PVC on uninstall; StatefulSet claim
templates also retain their claims by default. Review claims before reinstalling
under an old release name. Do not assume helm rollback rolls back database schema.

Changing database.mode does not migrate data. Snapshot SQLite, pause ingestion,
import into an empty PostgreSQL target with scripts/migrate_sqlite.py, verify row
counts and sample queries, then change the chart mode. Retain the snapshot/old
volume for rollback. Schema migrations reject a newer unsupported DB version.

Secrets are external. Rotating one requires a rollout restart of the gateway and
collector, then updating clients. This chart intentionally does not generate
credentials or store them in Helm release history.

## Durable collector queue

OTLP logs/traces use file_storage on a dedicated collector PVC, bounded to 1000
queued requests with retries. This improves restart durability; it is not an
exactly-once guarantee. Queue exhaustion/disk loss still causes telemetry loss,
and logs may duplicate after retries. The Prometheus exporter's metric state is
in memory and is not protected by the log/trace disk queue.

## Verification

    helm lint deploy/helm/montralog --strict
    python scripts/check_chart.py

The chart checker renders both profiles and checks security/storage invariants
and invalid combinations. Runtime checks must also verify ingress/TLS, production
storage class, CNI enforcement, backups, alert delivery and actual node failures.
See VERIFICATION.md for evidence from this machine.

Browser accounts, session endpoints and personal dashboards are described in [ACCOUNTS.md](ACCOUNTS.md). Browser sessions have telemetry read access; ingestion still requires the separate ingest bearer token.
