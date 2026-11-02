# Montralog 0.8.1

Build separate dashboards for systems and applications, edit panels on a visual canvas, connect supported telemetry backends and optionally ask your approved model to propose panels.

## Dashboard and connection improvements

- Dashboard card library with search, duplication and switching. Each personal dashboard supports **0–24 panels**; starter counts are not limits.
- Windows (8 panels), Linux (10), infrastructure, application and incident starters. Collectors/exporters must be connected; the Windows starter uses Montralog host metrics, not a native windows_exporter adapter.
- Per-panel editing, selection, multi-preset addition, live previews, expanded inspection, icons, references, widths, heights, thresholds and guided aggregations with generated metric queries.
- Dark, Light, Midnight and System themes under **Settings → Appearance**, retained per browser.
- Loki sampled logs/patterns, Tempo trace summaries, and VictoriaMetrics/Mimir/Thanos through their compatible Prometheus query APIs. Missing telemetry is shown explicitly. See [adapter limits](STUDIO.md#external-backend-adapters).

## AI-assisted creation

Administrators can generate 1–6 supported panel proposals per request through local Ollama or approved provider profiles, then review or append them to a draft. Generation does not save a dashboard, query telemetry or change infrastructure. Check sources, thresholds and filters before saving; titles are not semantic proof.

The worker rechecks role, provider and sharing policy. Only the description and supported metric catalogue are sent for panel drafts. Hosted requests require operator-enabled egress and explicit user approval. Provider keys remain server-side. Jobs share existing budgets; optional scoped workers separate panel generation from longer investigations. Existing read-only investigation/runbook boundaries remain unchanged.

## Security and correctness

Pin `joserfc` to 1.7.6 after dependency audit findings. Add worker ownership/policy tests, SQLite/PostgreSQL queue coverage, browser multi-panel/AI append tests and logout draft isolation. Bind SQL LIKE patterns as parameters for PostgreSQL compatibility. Keep Apache-2.0 and bundled attribution unchanged.

## Upgrade and rollback

Docker Compose is the supported installation path. Back up application data and the matching encryption key **before** upgrading. Preserve `.env`, customer identity, tokens and volumes. Upgrade **all** Montralog services, including retention, notifications and optional AI workers, to `ghcr.io/montralog/montralog:0.8.1`; use the published digest for reproducibility.

This release uses **schema 8**, which records the backend type on saved connections. Existing connections migrate as Prometheus. Older schema-7 binaries cannot open the migrated database. Rollback requires the pre-upgrade database backup **and matching encryption key**, not just an older container tag. Do not rotate keys or reinitialize a live stack as an upgrade step. See [Docker upgrade/restore](CONTAINERS.md) and [assurance](ASSURANCE.md).

## Evidence and boundaries

The gated release attaches exact-image scan reports, dependency inventory/SBOM, browser results, bootstrap/load/recovery measurements, local-model evaluation, checksums and image identity. Provenance accompanies the published image. Publication is complete only when the workflow and release assets exist.

[Dashboard development evidence](reports/dashboard-creation/README.md) includes actual synthetic Ollama results and limitations. Automated scans and short synthetic tests do not establish external security certification, sustained capacity or root-cause accuracy. Customer isolation remains separate Docker stacks; teams/groups do not provide shared-database tenant isolation. External log/trace panels are not captured by the AI investigation evidence path.
