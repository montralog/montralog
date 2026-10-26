# Isolation, backup and reliability assurance

Montralog supports a separate Docker Compose stack per customer. It does not implement shared-database SaaS tenancy. Never attach two customer projects to the same database, volume, credentials or encryption key. The host administrator remains trusted and can access all stacks; use separate hosts/accounts where that boundary is insufficient.

## Provision and audit

Use `scripts/create_tenant.py` through the Docker helper documented in [TENANCY.md](TENANCY.md). It generates a distinct project, identity, machine tokens and encryption key, refuses existing files and overlapping ports. Before operating several customers, run the offline audit:

```sh
docker run --rm --entrypoint python -v "${PWD}:/install" ghcr.io/montralog/montralog:0.7.0 /install/scripts/silo_config.py audit --directory /install/.local/tenants
```

The audit reads private files without printing secret values. It rejects repeated identities, projects, master keys, tokens and port assignments. It cannot discover databases mounted outside those configuration files; inspect the resolved Compose mounts and project names as well. Keep the entire private directory access restricted.

Strict mode requires customer-bound read and ingest tokens. New managed API tokens also carry a customer namespace. Database binding checks the customer ID and master-key fingerprint. New `enc:v2` integration ciphertext uses a customer-derived key; copied ciphertext is rejected under another customer identity even with a reused master. The offline audit still forbids master-key reuse. Operators holding a master key are trusted and can derive keys; this is not protection against the host administrator.

## Upgrade from 0.6

Back up with the old image first, preserve its original environment and stop writes. Generate a new configuration without overwriting the old one:

```sh
docker run --rm --user 0:0 --entrypoint python -v "${PWD}:/install" ghcr.io/montralog/montralog:0.7.0 /install/scripts/silo_config.py upgrade --source /install/.env --output /install/.env.upgraded
```

The helper preserves the exact customer ID and master key and rotates machine tokens. Update your producers/collectors with the new ingest token, then use the new file with `docker compose --env-file .env.upgraded ...`. Reissue legacy managed API tokens: strict mode rejects their old format. Start the new image, run `encrypt-secrets` and `verify-secrets` before restoring traffic. Schema 7 upgrades plaintext and v1 integration records to v2 through the explicit encryption command. Wrong-key records cause failure instead of silent replacement. Never change the customer identity of an existing database.

## Verified SQLite backups

Create a unique backup name in `/data`:

```sh
docker compose exec gateway python -m montralog backup --destination /data/snapshot-001.db
docker compose exec gateway python -m montralog verify-backup --source /data/snapshot-001.db
docker compose cp gateway:/data/snapshot-001.db ./snapshot-001.db
docker compose cp gateway:/data/snapshot-001.db.manifest.json ./snapshot-001.db.manifest.json
```

The command exclusively creates private files and refuses overwrite. Linux checks ownership and unsafe parent permissions; Windows operators must also restrict file ACLs. Preserve the manifest beside the backup and store the original key separately in protected recovery storage. The manifest validates SHA-256 integrity, schema, customer identity and key fingerprint, followed by SQLite integrity and integration decryption checks. It is not a signed authenticity proof against someone who can replace both files.

For a restore drill, stop application writers and restore to a new path in an isolated project using the original customer ID and key:

```sh
docker compose exec gateway python -m montralog restore-backup --source /data/snapshot-001.db --destination /data/restored-001.db
```

This command never replaces the live database. Point a separate stopped recovery project at the verified restored file, set ownership for UID/GID 10001 and verify accounts, record counts, integrations, receipts and notifications before cutover. Run the command while gateway is available, then stop all writers before switching databases. Version 0.6 backups lack this manifest: restore them using the original image/configuration first, then upgrade. These commands do not back up Prometheus or collector volumes; preserve those separately. PostgreSQL requires native backup/PITR and a separate restore drill.

A wrong key or another customer's backup is rejected. If every copy of a key is lost, encrypted credentials cannot be recovered. Restore the original key from protected backup; otherwise follow an operator-reviewed integration re-provisioning procedure. There is no decryption bypass.

## Delivery guarantees and tests

Native JSON and OTLP log/trace ingestion accept an optional `Idempotency-Key` of 16–128 URL-safe characters. Use the same key and identical body on retry. A key is scoped to customer, credential and endpoint, retained for 24 hours and committed atomically with the records. A changed body returns 409. Without a key, or after expiry, a retry may duplicate records. The metrics forwarding endpoint does not accept this guarantee.

Alert evaluation retains the last known firing state across source outages. Source recovery does not create another firing notification; recovery to normal queues resolution. Workers lease bounded outbox batches, reclaim expired leases and stop after five failed attempts. Delivery is **at least once**: a receiver accepting a message before a worker crash can see a duplicate. Slack delivery cannot be exactly once.

`scripts/reliability_soak.py` exercises synthetic ingestion, concurrent retries, queries, restarts, backup/restore and alert-delivery failures against an isolated image. Reports include duration, measured throughput, latency, acknowledgments, stored counts and errors. Short controlled tests are regression evidence, not a capacity/SLA or long-duration endurance certification. Scanners find known patterns; see the independent-agent review and release evidence for findings and limitations. A third-party penetration test and deployment-specific sustained load test remain separate acceptance work.

Login throttles apply to source/username, source, username and global budgets. Shared NAT users can consume the same source budget. Configure the front proxy's rate limits too; do not assume untrusted forwarding headers identify clients.
