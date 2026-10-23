# Montralog Helm chart

Chart **0.5.0-rc.2** deploys application **0.5.0-rc1**. This public preview has hosted kind-cluster checks for SQLite and the PostgreSQL topology; validate your own cluster before production use.

## Included resources

- Gateway Deployment and Service, health probes and resource settings.
- SQLite application PVC with a retention sidecar, or an external PostgreSQL connection with a retention CronJob.
- Persistent OpenTelemetry Collector and optional Prometheus/Alertmanager backends.
- Singleton notification worker, optional TLS ingress, NetworkPolicy and disruption-budget settings.

Templates are under [templates/](https://github.com/montralog/montralog/tree/main/deploy/helm/montralog/templates/); settings are in [values.yaml](https://github.com/montralog/montralog/tree/main/deploy/helm/montralog/values.yaml), the [production example](https://github.com/montralog/montralog/tree/main/deploy/helm/montralog/values-production.yaml) and [values.schema.json](https://github.com/montralog/montralog/tree/main/deploy/helm/montralog/values.schema.json).

## Prerequisites

Kubernetes 1.27+, Helm 3, a working persistent-volume storage class and a Montralog image built and pushed to your own registry. The public Helm repository is https://montralog.github.io/montralog. No public application image is published yet; build and push your own image before installation.

Create namespace `observability`. Create a Secret named `montralog-auth` in that namespace containing distinct random `read-token` and `ingest-token` values of at least 32 characters each. Use protected files or a secret manager. Keep secret values out of Git, Helm values and command history. See the full [credentials guide](https://github.com/montralog/montralog/blob/main/docs/KUBERNETES.md#credentials).

## Install the released chart

Add the repository, then replace the registry placeholder with your application image:

```sh
helm repo add montralog https://montralog.github.io/montralog
helm repo update
helm upgrade --install montralog montralog/montralog --version 0.5.0-rc.2 --namespace observability --create-namespace --set auth.existingSecret=montralog-auth --set image.repository=YOUR_REGISTRY/montralog --set image.tag=0.5.0-rc1 --wait --timeout 5m
```

From a source checkout, replace `montralog/montralog` with `./deploy/helm/montralog`.

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

See [Kubernetes operations](https://github.com/montralog/montralog/blob/main/docs/KUBERNETES.md), [storage](https://github.com/montralog/montralog/blob/main/docs/STORAGE.md) and [production readiness](https://github.com/montralog/montralog/blob/main/docs/PRODUCTION.md) for the complete requirements.
