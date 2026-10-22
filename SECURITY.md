# Security policy

This release candidate has no independent security audit. Intended for one trusted
organization in a protected network. Read-token holders access all telemetry.
Ingest-token holders can submit spoofed service names/events. This is role
separation, not granular RBAC, tenant isolation or source attestation.

Use distinct random tokens, remote HTTPS and restricted file/network/backup access.
SQL values are parameterized, static routes and metric queries allowlisted, and
responses have CSP/no-store/nosniff headers. Redaction is heuristic.
No automatic remediation or language-model execution is present.

Known gaps: no per-source application rate limiting, comprehensive audit log,
built-in gateway TLS, tenant authorization or independent pipeline
monitoring. Apply front-proxy limits and protect the internal network. Helm supports
TLS ingress and NetworkPolicy; enforcement depends on the cluster. Collector
log/trace queues persist to a volume/PVC and remain bounded.

Docker uses a one-shot root initializer limited to CHOWN on its dedicated collector
volume. It mounts no host paths or Docker socket. Gateway/collector run as uid 10001;
Helm uses fsGroup for volume access.

Report vulnerabilities privately using the repository Security tab / Report a vulnerability. Do not include credentials or sensitive telemetry in public issues. This early public preview has no guaranteed response-time SLA or stable-version support window.

Browser account security and limitations are documented in docs/ACCOUNTS.md. Local accounts share telemetry read access; there is no tenant isolation. Identity-provider setup and boundaries are documented in docs/IDENTITY.md. Access changes have a limited audit history; it is not a tamper-proof compliance log.
