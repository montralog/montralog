# Release and support policy

The current non-RC release is **0.6.0**. The maintained public line is the latest `0.6.x` release. Earlier RC builds are historical evaluation snapshots; organization deployments should follow the current release's upgrade instructions. Versioned image tags and release archives are retained; changed application content requires a new version.

Supported published container platform: Linux/amd64. Supported installation: Docker Compose, with separate projects per customer. Older Helm artifacts are retained for compatibility. Storage profiles: SQLite with one gateway, or an operator-managed PostgreSQL backend with shared gateway storage. Supported automated Python test versions: 3.11 and 3.13. Browser acceptance runs in Chromium. Other targets need explicit validation before support claims are added.

Use public issues for reproducible, sanitized bugs. Report vulnerabilities privately through GitHub Security Advisories. Community maintainers provide support without a guaranteed response SLA. Organization operators own their infrastructure, tenant registrations, destination credentials, operational objectives and recovery plans.

A non-RC version identifies a maintained release; environment-specific production validation and security review remain required. Release scan reports describe their image/database snapshot, not the absence of all vulnerabilities at all future times. New advisories and dependencies are reviewed through the repository's security checks and alerts.
