# Security policy

Supported release: **0.6.0**. See [security changes and encrypted-credential upgrade instructions](docs/SECURITY-0.5.1.md). Earlier previews should upgrade. See docs/SUPPORT.md for the maintained release line and support scope.

This release has no independent security audit. Each Docker stack is scoped to one trusted customer in a protected network. Read-token holders access all telemetry.
Ingest-token holders can submit spoofed service names/events. Within a customer, this is role separation rather than granular RBAC or source attestation. [Silo tenant boundaries](docs/TENANCY.md) isolate separate Docker stacks; shared-database hosting is disabled.

Use distinct random tokens, remote HTTPS and restricted file/network/backup access.
SQL values are parameterized, static routes and metric queries allowlisted, and
responses have CSP/no-store/nosniff headers. Redaction is heuristic.
No automatic remediation or language-model execution is present.

Known gaps: no per-source application rate limiting, comprehensive audit log,
built-in gateway TLS, shared-gateway tenant authorization or independent pipeline
monitoring. Apply front-proxy limits and protect the internal network. Helm supports
TLS ingress and NetworkPolicy; enforcement depends on the cluster. Collector
log/trace queues persist to a volume/PVC and remain bounded.

Docker uses a one-shot root initializer limited to CHOWN on its dedicated collector
volume. It mounts no host paths or Docker socket. Gateway/collector run as uid 10001;
Helm uses fsGroup for volume access.

Report vulnerabilities privately using the repository Security tab / Report a vulnerability. Do not include credentials or sensitive telemetry in public issues. Community vulnerability response has no guaranteed SLA; the latest 0.6.x release is maintained.

Browser account security and limitations are documented in docs/ACCOUNTS.md. Local accounts share telemetry read access within their customer stack. Identity-provider setup and boundaries are documented in docs/IDENTITY.md. Access changes have a limited audit history; it is not a tamper-proof compliance log.

Release images use a pinned Alpine runtime. Publication rejects every reported HIGH/CRITICAL image vulnerability, including unfixed findings, and requires nonempty OS/Python scan inventories. Reports are a point-in-time scan, not a universal security guarantee. Docker and Helm require an operator-held encryption key by default; migrate existing plaintext integration records explicitly after backup.
