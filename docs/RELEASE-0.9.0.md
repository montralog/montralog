# Montralog 0.9.0 — workspace and dashboard improvements

Release candidate: publication is confirmed only by the versioned GitHub release and its artifacts. Existing 0.8.2 images and historical reports are unchanged.

## Changes

- Dashboard cards show panel layout, signal types and time window, with compact open/edit/duplicate/delete controls.
- Add panels directly from a saved dashboard. The desktop inspector reserves canvas space; presets support multiple selection. Drag reorder or use keyboard Move up/Move down, then save. Each dashboard supports up to 24 panels.
- Administrators can update the organization display name and description in Settings. Values persist, viewers cannot edit them, and updates are audited. Appearance controls remain in Settings.
- Dashboard reads render progressively with up to four queries in flight and deduplicate identical queries per render. Navigation cancels obsolete work; slow queries do not block the canvas.
- Local log browsing uses bounded cursor pagination rather than counting every matching row. Cursor snapshots exclude later arrivals, including backdated records.
- Data-source setup explains backend-specific URL prefixes and limits. HTTP contract tests exercise all six external adapters. Malformed source responses return controlled gateway errors.
- Updated screenshots, connection instructions, AI configuration links and upgrade guidance. Configurable AI panel proposals remain drafts requiring explicit review and save; local Ollama was exercised with synthetic requests.

## Upgrade and rollback

Database schema advances from **8 to 9**, adding organization display settings. Back up the database and preserve its matching encryption key before upgrading. Test backup restoration in an isolated stack. Preserve customer identity, credentials, keys and volumes; upgrade gateway and all workers together. Docker Compose is the supported simple installation path. Helm compatibility remains gated by cluster smoke tests.

Schema-8 binaries cannot open schema-9 databases. Rollback requires the pre-upgrade database backup and its matching key, not simply an older image tag. See [Docker installation](CONTAINERS.md), [storage](STORAGE.md), [recovery](ASSURANCE.md) and [workspace workflows](WORKSPACE-PREVIEW.md).

## Evidence and limits

The gated release reruns application tests on Python 3.11/3.13, browser tests, container checks, Helm deployment smoke tests, local-model evaluation, resilience checks and security scans. Exact-image bootstrap, load and recovery checks run before image publication. The release attaches reports, a dependency SBOM, image digest and checksums. These are scoped verification evidence, not independent penetration-testing certification.

The [synthetic ten-million-record read benchmark](reports/dashboard-scale/README.md) measures SQLite query behavior, not production ingestion throughput, arbitrary filters or concurrent capacity. Source HTTP fixtures verify adapter contracts, not every vendor deployment. Loki remains a 100-record sample with service_name labels; Tempo provides trace summaries, not a full waterfall. Tenant-header backends require a trusted operator-managed gateway.

Bundled upstream images retain the exact-digest security exceptions documented in [0.8.2 notes](RELEASE-0.8.2.md). Four previously accepted HIGH occurrences remain scoped to their exact image/CVE/package/version/count. Current scans must pass the existing policy; new/unapproved highs and every critical fail. All findings remain in reports and Artifact Hub scans. No previous scan count is presented as a new scan.

See [model configuration](../README.md#configure-your-ai-model) and [data-source setup](CONNECTIONS.md).
