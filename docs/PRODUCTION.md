# Production readiness

0.5.1 is the maintained non-RC release. A clean local installation and automated tests do not establish production capacity or availability. Validate your organization rollout before replacing existing monitoring.

Before relying on a deployment, record evidence for each item:

| Area | Required evidence |
|---|---|
| Access | HTTPS, secure cookies, restricted network access, individual accounts and appropriate roles |
| Secrets | Protected environment files, database and backups; rotation procedure |
| Recovery | Restore a backup into a separate deployment and verify accounts, dashboards and telemetry |
| Capacity | Representative ingestion/query load, retention, disk usage and overload behavior |
| Alerts | Actual firing, resolution and destination receipt; receiver outage behavior |
| Failure | Restart, backend outage and full-disk behavior; independent monitoring of the pipeline |
| Dependencies | Scan the exact built image and review dependency licenses before distribution |
| Upgrade | Backup and restore rehearsal; do not downgrade a migrated database in place |
| Kubernetes | Validate the chart on your cluster, storage class, network policy, TLS and registry |
| Operations | Named maintainers, incident response and a private security reporting channel |

SQLite deployment uses one gateway. PostgreSQL can share application storage across gateways, but does not make Prometheus, the collector or the entire system highly available. Notification evaluation remains a singleton worker.

Integration credentials support authenticated encryption with an operator-held key. Existing plaintext records require the [explicit migration](SECURITY-0.5.1.md); telemetry and whole databases are not encrypted by this feature. Local accounts share telemetry within one organization. Company sign-in needs registration and live validation. There is no tenant isolation, independent security audit or published capacity guarantee.

Use the operations, security and Kubernetes guides for deployment details. Treat each unchecked item above as outstanding work for your environment.
