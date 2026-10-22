# Workspace update verification — 2026-10-22

Version: 0.2.1-rc1. Performed locally on the existing Docker installation.

- 45 automated tests passed against SQLite and a disposable PostgreSQL 17.6
  database. Coverage includes existing telemetry behavior, account sign-in,
  password verification, CSRF rejection, session expiry, logout revocation,
  password-change revocation, other-session revocation, secure cookie mode,
  profile storage, dashboard validation and isolation between account owners.
- Helm checks passed: SQLite (17 resources), PostgreSQL (19 resources), and
  rejection of seven unsupported configurations. Strict Helm lint passed.
- Live Docker smoke checks passed: readiness, unauthorized read rejection,
  token role separation, ingestion, log patterns and trace correlation.
- Collector round-trip passed for logs, traces and metrics, including rejection
  of an invalid ingestion token and application metrics queried through Prometheus.
- Browser checks passed: dedicated sign-in screen; successful account sign-in;
  dashboard creation/opening with real scrape metrics; profile save; profile and
  session controls; persistent session after gateway replacement; sign-out and
  continued signed-out state after reload.
- The existing telemetry volume and API credentials were preserved. A SQLite
  backup was created before migration at /data/pre-accounts-20261022.db inside
  the existing volume. Source rollback files are under work/upgrades locally.
- An initial local account was generated for this installation. Its password is
  in a separate private local login file, excluded from source and release bundles.

The account-enabled chart was rendered and validated; it was not installed into
a new Kubernetes cluster during this update. Previous 0.2 cluster evidence does
not substitute for testing this version in the target cluster. This remains a
release candidate: local tests do not establish production capacity, availability,
SSO, tenant isolation, independent security review or external alert delivery.
