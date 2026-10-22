# Access and identity verification — 2026-10-22

Release 0.5.0-rc1; schema 5.

- SQLite/general regression run: 107 test executions, 65 passed and 42 PostgreSQL cases skipped because that run had no PostgreSQL URL.
- Separate disposable PostgreSQL 17.6 run: 55 tests passed, no skips, including role protection, team/group membership, identity-token rejection and a mocked complete sign-in exchange.
- Targeted current identity tests: six checks cover provider profiles, rejected JWT claims/signatures, browser binding/replay, secret-safe settings, viewer provisioning without email linking, and PKCE/start limits. These include local signed test tokens and mocked provider responses, not live organization credentials.
- Helm: SQLite and PostgreSQL profiles render with security/storage assertions; seven invalid configurations rejected.
- JavaScript syntax checked; Docker image built successfully.
- Existing local database backed up consistently before migration; schema upgraded from 4 to 5. Four saved dashboards preserved. Read-only installation check passes with two healthy Prometheus targets.
- Browser verified People & access, team/group creation and membership changes. Starter team Platform engineering contains the existing administrator; Operations group is empty.

Provider sign-in is implemented for the documented issuer profiles, but no real Microsoft, Google or Okta tenant registration was supplied. Live login, upstream MFA/assignment behavior and provider outages remain unverified. Company directory synchronization, SCIM, inherited group permissions, custom roles, per-team telemetry isolation and vendor audit-event polling are not implemented.

This is an evaluation candidate, not an independently audited production identity platform. Keep a local recovery administrator and validate the identity and production guides before deployment.
