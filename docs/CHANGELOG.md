# 0.5.1-rc1 — security-focused preview

- Authenticated encryption for saved integration credentials, with operator-held keys and explicit transactional migration for existing records.
- Safe private-key generation for upgrades and generated keys for new setups.
- Hardened Docker build-context exclusions and built-image sentinel checks.
- Refreshed pinned Python base; dependency, static-code and image security gates.
- Version alignment and gated release assets: source, wheel, source distribution, Helm package, dependency inventory and checksums.
- Includes the executed functional-review corrections documented below.

See [release notes](RELEASE-0.5.1.md) and [security upgrade instructions](SECURITY-0.5.1.md).

# Unreleased functional review fixes — 23 October 2026

- Reject malformed nonfinite Prometheus JSON without crashing HTTP response serialization.
- Reject boolean alert numbers and fractional waiting periods.
- Keep missing/nonfinite metric samples from breaking bar charts.
- Add targeted SQLite/PostgreSQL regressions, dashboard component tests and an isolated HTTP/restore check.
- Load platform-specific images in Kubernetes CI to avoid incomplete OCI-index imports.
- Publish chart 0.5.0-rc.2 with the README, license, logo and project links; retain the original chart.

These source changes require rebuilding your application image. The application metadata remains 0.5.0-rc1; no new application binary release is claimed.
See [the executed functional review](FUNCTIONAL_REVIEW-2026-10-23.md).

# 0.5.0-rc1 — public preview



- Administrator/viewer role management with last-administrator protection.

- Organizational teams/groups, membership controls and access-change history.

- Microsoft Entra ID, Google Workspace and Okta OIDC configuration with PKCE, single-use browser-bound state and signed-token validation.

- Separate viewer identities keyed by provider, issuer and subject; no email-based linking or external-admin inheritance.

- Schema 5, current documentation index and consistent Montralog brand assets.

- No directory synchronization, per-team telemetry isolation or vendor audit-event polling in this candidate.



# 0.4.0-rc1



- Guided Prometheus source catalog and server URL/authentication setup.

- Real connection tests, saved defaults, editing and private credential storage.

- Per-panel data source selection, preserving the bundled source as a fallback.

- Versioned schema 4 and connection security/regression tests on SQLite/PostgreSQL.



# 0.3.0-rc1



- Mixed-signal dashboard and panel editing: line, bar, statistic, table and timelines.

- Administrator-managed expiring read/ingest API tokens and gateway OTLP metric forwarding.

- Metric/log alert conditions, in-app inbox, private Slack contact points and persisted delivery retries.

- SQLite schema 3 preserves telemetry, accounts and earlier dashboards; PostgreSQL remains optional.



# 0.2.1-rc1



- Local browser accounts, hashed passwords, expiring revocable sessions and CSRF protection.

- Dedicated sign-in page, profile editing, password change and session controls.

- Personal saved dashboards, four templates, data source status and settings.

- Schema migration preserves existing telemetry; collector bearer authentication continues.



# Changelog



## 0.2.0-rc1 â€” 2026-10-22



Modular src layout, packaged browser assets, independent host agent, and separate

Docker/Helm deployments. PostgreSQL storage, ordered schema adoption, bounded DB

waits, batched retention and SQLite import. Helm/schema, existing Secrets, TLS

ingress, probes, persistent queues, network policy, disruption budget and replicated

PostgreSQL profile. Storage/chart/runtime checks and shared Gunicorn configuration.



## 0.1.0-rc1 â€” 2026-10-22



Initial single-organization pilot candidate: service overview, logs, message

patterns, trace timing, change events, host agent, fixed Prometheus dashboards,

JSON/OTLP JSON adapters, Docker files, retention/backup tools, tests and CI.



Not a stable production release. See docs/VERIFICATION.md and docs/RELEASE.md.
