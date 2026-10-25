# Production and SaaS acceptance

Supported customer hosting uses [isolated Docker stacks](TENANCY.md). Shared application/database SaaS hosting is disabled. A stable release or clean scan alone does not establish production readiness.

| Requirement | Automated evidence | Deployment acceptance still required |
|---|---|---|
| Credential transport / SSRF | HTTPS saved credentials, no redirects/proxies, exact private-origin approval, DNS validation and IP pinning | HTTPS ingress, trusted DNS, egress restrictions; internal Collector HTTP stays on its private network |
| Customer isolation | Per-stack database, tenant-bound transactions/cookies, rejected cross-customer tokens/sessions | Distinct env files, keys, networks, volumes and TLS routes; protected Docker operator access |
| Secret recovery | Fresh/legacy migration, idempotence, wrong-key rollback, encrypted backup restoration and lost-key rejection | Separate key backups and staging restore; PostgreSQL native recovery if used |
| Ingestion/query load | Concurrent synthetic requests, throughput, p50/p95 latency and acknowledged/stored/missing counts | Sustained representative workload, retention/disk sizing and noisy-neighbor testing |
| Failures/alerts | Explicit 503 write retry, gateway restart, persisted alert retries and worker-process recovery | Actual Slack receipt/resolution, long outages, disk-full/host failure and independent pipeline monitoring |
| Supply chain | Exact-image all-severity scan, dependency/static reports, digest, checksums and provenance | Current advisory review, accepted lower-severity findings and patch ownership |
| Operations | Probes, non-root containers and backup commands | Named maintainers, TLS/cookies, incident response and upgrade/rollback rehearsal |

[Public evidence](reports/README.md) identifies the version, workload and limits. Short load measurements are not sustained capacity guarantees. API retries after an ambiguous network failure can duplicate events; transactional acknowledgements do not establish exactly-once delivery. Slack delivery is at-least-once and can duplicate if a worker crashes after sending but before persisting its acknowledgement.

SQLite is not HA. Optional PostgreSQL does not make the whole stack HA. Host/root operators remain trusted. Entra/Google/Okta registrations and Slack destinations need live customer validation. Independent security certification and a shared-gateway SaaS control plane have not been established.
