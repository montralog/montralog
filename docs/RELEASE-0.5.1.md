# Montralog 0.5.1-rc1 — security-focused public preview

Application: **0.5.1-rc1**. Python package: **0.5.1rc1**. Helm chart: **0.5.1-rc.1**. Database schema remains **5**.

This version releases the executed functional-review fixes and additional security work together as one tagged source snapshot. It remains a preview for controlled pilots, with no independent security audit or production capacity guarantee.

## Changes

- Encrypt saved Prometheus credentials, Slack webhooks and OIDC client secrets when an operator-held key is configured; generate a key for new Docker setups.
- Add an explicit, transactional and idempotent migration for existing plaintext integration credentials.
- Exclude private env files, key files, databases and local credentials from Docker builds; verify exclusions against the actual built image.
- Refresh the pinned official Python base and introduce dependency, static-code and image security gates.
- Include the reviewed fixes for malformed Prometheus responses, invalid alert numbers and missing chart samples.
- Include SQLite/PostgreSQL regression, HTTP ingestion/restore, Docker and Kubernetes tests, plus a documented Helm chart and Artifact Hub integration.

## Install and upgrade

Start with the repository quickstart or chart README. Read [the security upgrade guide](SECURITY-0.5.1.md) before enabling encryption on an existing deployment. Back up the database and preserve the key separately. Old application versions cannot read the new encrypted integration fields; rollback requires a pre-upgrade database backup and its matching configuration. Avoid changing database mode during this upgrade.

Build your own application image from this tag and push it to your registry for Kubernetes. This release does not claim a published public application container. Verify downloaded assets with `SHA256SUMS.txt`. Checksums provide integrity checks, not an independent publisher signature.

Release assets include the tagged source archive, Python wheel/source distribution, Helm package, checksums and dependency inventory. The release workflow executes functional and security gates before publishing these assets. Exact scan evidence is linked from the workflow; known unfixed OS findings, if present, remain in the full image report.

## Scope

Live tenant SSO, Slack destination receipt, full browser end-to-end tests, sustained load and production incident recovery remain deployment-specific. Credentials without a configured key remain in legacy compatibility mode until migrated. See the security policy and production checklist.
