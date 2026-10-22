# Montralog Helm chart

Chart **0.5.0-rc.1** deploys application **0.5.0-rc1**. This public preview has hosted kind-cluster checks for SQLite and the PostgreSQL topology; validate your own cluster before production use.

## Included resources

- Gateway Deployment and Service, health probes and resource settings.
- SQLite application PVC with a retention sidecar, or an external PostgreSQL connection with a retention CronJob.
- Persistent OpenTelemetry Collector and optional Prometheus/Alertmanager backends.
- Singleton notification worker, optional TLS ingress, NetworkPolicy and disruption-budget settings.

Templates are under [templates/](templates/); settings are in [values.yaml](values.yaml), the [production example](values-production.yaml) and [values.schema.json](values.schema.json).

## Prerequisites

Kubernetes 1.27+, Helm 3, a working persistent-volume storage class and a Montralog image built and pushed to your own registry. No public application image or Helm repository index is published yet. The chart can be installed from source or its release archive.

Create namespace `observability`. Create a Secret named `montralog-auth` in that namespace containing distinct random `read-token` and `ingest-token` values of at least 32 characters each. Use protected files or a secret manager. Keep secret values out of Git, Helm values and command history. See the full [credentials guide](../../../docs/KUBERNETES.md#credentials).

## Install the released chart

Download the chart from the [v0.5.0-rc1 release](https://github.com/montralog/montralog/releases/tag/v0.5.0-rc1) and verify its published SHA-256 checksum. Then replace the example registry with your image:

```sh
helm upgrade --install montralog ./montralog-0.5.0-rc.1.tgz   --namespace observability --create-namespace   --set auth.existingSecret=montralog-auth   --set image.repository=YOUR_REGISTRY/montralog   --set image.tag=0.5.0-rc1   --wait --timeout 5m
```

From a source checkout, replace the archive path with `./deploy/helm/montralog`.

```sh
kubectl -n observability get deployments,statefulsets,pods,pvc
kubectl -n observability exec -it deployment/montralog -c gateway --   python -m montralog create-user --username admin --name Administrator
kubectl -n observability port-forward svc/montralog 8080:8080
```

Open http://localhost:8080 and use the account you created. No default shared password is installed.

## Important settings

| Value | Purpose |
|---|---|
| `image.repository`, `image.tag`, `image.digest` | Your application image; prefer an immutable digest after validation |
| `auth.existingSecret` | Existing read/ingest credential Secret |
| `database.mode` | `sqlite` (one replica) or `postgresql` (external DB) |
| `database.existingSecret`, `database.urlKey` | PostgreSQL connection Secret and key |
| `persistence.storageClassName`, `persistence.size` | Application storage class and size |
| `replicaCount` | Gateway replicas; values greater than one require PostgreSQL |
| `ingress` | Optional host, TLS and ingress-controller settings |
| `prometheus.extraScrapeConfigs` | Exporters you already operate; exporter installation is separate |
| `prometheus.externalUrl` | Required when bundled Prometheus is disabled |
| `networkPolicy.extraEgress` | Additional egress for exporters, providers and notification destinations |
| `alertmanager.existingConfigSecret` | Optional Alertmanager configuration; default receiver sends no external messages |

## Production and upgrades

Copy `values-production.yaml` into operator-controlled configuration, replace its registry/host/Secret placeholders, and provision the external database and TLS Secret. The sample is not a production availability guarantee: Prometheus and Collector remain single instances. Make sure the cluster CNI enforces NetworkPolicy and permits your needed outbound destinations.

Back up data before every upgrade. `helm rollback` does not reverse database migrations. SQLite remains single-replica; changing database mode does not migrate data. Existing PVCs may remain on uninstall. Review storage and restore procedures before removing a release.

See [Kubernetes operations](../../../docs/KUBERNETES.md), [storage](../../../docs/STORAGE.md) and [production readiness](../../../docs/PRODUCTION.md) for the complete requirements.
