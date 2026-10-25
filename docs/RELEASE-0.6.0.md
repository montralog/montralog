# Montralog 0.6.0

Docker installation, customer isolation and reproducible security/recovery evidence. Application/Python/chart version: **0.6.0**. Database schema: **6**.

## Functional and security changes

- Saved Basic/bearer credentials require HTTPS. Outbound requests validate DNS answers and pin numeric connection IPs while preserving normal TLS hostname verification. Private destinations require an exact operator allowlist entry; metadata/link-local destinations and redirects are always rejected. Slack and OIDC use the same pinned transport. The internal Collector's HTTP credential transport is an explicit isolated-network exception, not available to saved sources.
- Customer isolation uses separate Docker projects, databases, encryption keys, tokens, networks, queues and backends. Every transaction validates the database's immutable tenant binding; session/OIDC cookies are scoped by tenant identity. Cross-customer tokens/sessions and mismatched tenant headers are rejected. Shared-database/gateway SaaS hosting is disabled.
- Docker-only setup needs no host Python. A customer bootstrap helper generates private, separate environment files and refuses overwrites/port reuse. Published older Helm artifacts remain available, while current installation documentation focuses on Docker.
- Read-only `verify-secrets` validates restored encrypted credentials and detects remaining plaintext. Regression coverage includes fresh migration, legacy plaintext, wrong-key rollback, encrypted backup restore and lost-key rejection. There is no recovery bypass for an irretrievably lost encryption key.
- A repeatable disposable-Docker acceptance probe measures ingestion throughput, concurrent query latency, acknowledged/stored/missing records, explicit storage failure retry, gateway restart, alert queue persistence and worker-process recovery. Slack delivery is stubbed and retry deadlines are advanced; no external messages are sent by the probe.
- Scan reports now retain all severities, inventories and static findings. The gate continues to reject every HIGH/CRITICAL finding, including unfixed findings. Release assets include the security, browser and acceptance archives, dependency SBOM, source/packages/chart, image digest and checksums. The published image includes GitHub build provenance.

## Install and upgrade

Use the [Docker guide](https://github.com/montralog/montralog/blob/v0.6.0/docs/CONTAINERS.md) and [customer isolation guide](https://github.com/montralog/montralog/blob/v0.6.0/docs/TENANCY.md). Preserve your existing configuration, tenant identity and encryption key; back up before upgrade. Existing configurations without `MONTRALOG_TENANT_ID` bind to `default`. Do not generate a new customer identity for an existing database or replace an active encryption key. Older images cannot read schema 6; rollback requires the matching old database/configuration backup.

Published platform: Linux/amd64. Pin the digest in `IMAGE_DIGESTS.txt` for production.

## Readiness and reports

See the [public evidence index](https://github.com/montralog/montralog/blob/main/docs/reports/README.md) and [production acceptance matrix](https://github.com/montralog/montralog/blob/v0.6.0/docs/PRODUCTION.md). Tests establish stated boundaries and failure scenarios, not sustained capacity, host compromise resistance, shared-gateway SaaS, whole-stack HA or independent security certification. Real customer TLS, egress, SSO, Slack receipt, backups, disk/host failures and representative sustained load require environment acceptance. Retried ingestion and notification delivery may duplicate events after ambiguous failures.
