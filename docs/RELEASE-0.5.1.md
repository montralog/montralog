# Montralog 0.5.1

Application, Python package and Helm chart: **0.5.1**. Database schema: **5**.

This non-RC release provides a public Linux/amd64 container at `ghcr.io/montralog/montralog:0.5.1`, linked to this repository under Packages. The `latest` tag is a convenience alias; pin the digest from `IMAGE_DIGESTS.txt` for production.

## What changed

- Replace the previous Debian runtime with a pinned Alpine 3.24 runtime. The release gate rejects every reported HIGH/CRITICAL finding, including unfixed findings, and rejects incomplete/unsupported scan reports.
- Require encryption keys by default in Docker and Helm. Preserve existing keys and explicitly migrate legacy plaintext integration credentials after backup.
- Publish the exact scanned image archive, verify its image ID/source revision, exercise its hardened startup, and require anonymous pull access with a matching registry digest before publishing the release.
- Publish GitHub build provenance for the container and attach its digest, source, Python distributions, Helm chart, dependency inventory, checksums and security reports to this release.
- Add browser acceptance tests for login/profile/logout, dashboard persistence, escaped log rendering/search and viewer authorization, plus regression cases for security gates.
- Include the previously reviewed ingestion, alert, dashboard, credential storage and collector redirect fixes.

## Install and upgrade

- [Docker installation](https://github.com/montralog/montralog/blob/v0.5.1/docs/CONTAINERS.md)
- [Organization rollout checklist](https://github.com/montralog/montralog/blob/v0.5.1/docs/ORGANIZATION_ROLLOUT.md)
- [Helm chart](https://github.com/montralog/montralog/tree/v0.5.1/deploy/helm/montralog)
- [Encryption and upgrade procedure](https://github.com/montralog/montralog/blob/v0.5.1/docs/SECURITY-0.5.1.md)

Back up the database and preserve the encryption key before upgrading. Existing `.env` files are never overwritten by setup. If no encryption key exists, create the private upgrade env file and supply it to all application processes, then run `python -m montralog encrypt-secrets`. Older application versions cannot read the encrypted integration fields; rollback requires the matching pre-upgrade database and configuration backup.

## Validation and operating scope

The release workflow requires Python 3.11/3.13 with SQLite/PostgreSQL tests, frontend component tests, real-browser acceptance, Docker/collector checks, Kubernetes SQLite/PostgreSQL installation and restart checks, dependency auditing, static analysis and strict container scanning. Image startup also checks the native PostgreSQL driver, non-root execution, encryption and architecture. The resulting reports are public release assets or workflow artifacts.

Supported deployment profiles are a single SQLite gateway or PostgreSQL-backed gateways for one trusted organization. Published container support is Linux/amd64. Validate your storage, TLS, NetworkPolicy, backups, load and alert destinations before organization rollout. The PostgreSQL profile does not establish HA for Prometheus or Collector. Live company SSO requires your provider registration and verification. There is no tenant isolation or independent security-audit certification. See the feature boundaries and support policy.

Security scan results are a snapshot for the release image. New advisories may appear later; use dependency alerts and review updates. An empty scan report is rejected rather than treated as a passing scan.
