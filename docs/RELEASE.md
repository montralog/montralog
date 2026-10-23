# Release status

Current version: **0.5.1-rc1**, a security-focused public preview for controlled pilots.

- [Versioned release notes](RELEASE-0.5.1.md)
- [Security changes and upgrade](SECURITY-0.5.1.md)
- [Executed functional review](FUNCTIONAL_REVIEW-2026-10-23.md)
- [Production validation still required](PRODUCTION.md)

Application, Python and Helm versions are aligned by release checks. Source, Python packages and the Helm chart are published as release assets only after functional and security gates pass. Build your own application container from the release tag.

Before upgrading, back up the database and preserve any encryption key separately. Encrypted integration fields are not readable by older application versions. Restore a pre-upgrade backup for rollback; schema migrations remain forward-only. No independent security audit, stable support SLA or production certification is implied.
