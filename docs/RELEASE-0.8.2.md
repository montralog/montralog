# Montralog 0.8.2 — bundled stack security maintenance

Update the pinned runtime and bundled Prometheus, Alertmanager and OpenTelemetry Collector images to address the findings reported for chart 0.8.1. The security pipeline now scans every bundled chart image and rejects new or unapproved HIGH/CRITICAL findings, while retaining all severity reports and package inventories. Artifact Hub scanning remains enabled; no images or findings are hidden.

- Prometheus: 3.16.0.
- Alertmanager: 0.35.0.
- OpenTelemetry Collector Contrib: 0.165.0.
- Refreshed Python 3.13 Alpine base, available Alpine package upgrades and pinned Trivy 0.76.2 scanner.

**Remaining known HIGH findings:** the stable Prometheus and Alertmanager images each contain two occurrences of `CVE-2026-78661` in `golang.org/x/net v0.61.0` (fixed in 0.62.0). The owner approved publishing the reduced findings with these disclosed. The CI acceptance is limited to those exact image digests, package/version/CVE and occurrence counts; all critical or new/unapproved high findings fail. Full scan output and Artifact Hub continue to display the accepted findings. Replace the images when upstream publishes a fix.

All image references are pinned by digest. Exact-image scans and workload checks must pass before publication. Reports are snapshots of the scanner database, not a guarantee against future advisories. Artifact Hub will update its grade after indexing and scanning the new chart version; historical 0.8.1 reports remain valid for that old image set.

Schema remains **8**. Back up data and the matching encryption key, preserve customer identity/tokens/volumes, and upgrade gateway and all workers together. For Helm installations also snapshot backend volumes and review upstream component release notes before upgrading. Rollback requires compatible database and backend snapshots, not only an older image tag. Docker Compose remains the supported new-installation path; chart compatibility is exercised in CI.

See the [security remediation evidence](reports/0.8.2/README.md), [Docker guide](CONTAINERS.md), [assurance guide](ASSURANCE.md) and [0.8.1 feature/migration notes](RELEASE-0.8.1.md).
