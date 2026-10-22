# Release status

**0.5.0-rc1 is a public preview for evaluation and controlled pilots.** It is not stable 1.0 or an independent production certification.

The repository includes source, Docker configuration, Helm chart, automated tests and setup documentation. Build your own container image; no public image is promised by this release. Use the changelog and versioned verification reports to understand what was tested.

Before production adoption, complete [PRODUCTION.md](PRODUCTION.md), including exact-image dependency/security review, backup restoration, representative load, alert delivery, target-cluster behavior and operator ownership. Before a stable release, establish a support policy, maintenance/review ownership and a security-response process. Private vulnerability reports are available in the repository Security tab.

Before upgrading, take and verify a backup. Schema migrations are forward-only. Restore a pre-upgrade backup for rollback; do not run older application code against a newer schema.
