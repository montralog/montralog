# Docker installation and operation

Requirements: Docker Engine/Desktop with Linux containers and Compose v2. Published images support Linux/amd64. Host Python, Helm and Kubernetes are not required.

## Install

Download the release source ZIP or check out its Git tag. From that folder in PowerShell or a POSIX shell:

```sh
docker run --rm --user 0:0 --entrypoint python -v "${PWD}:/install" ghcr.io/montralog/montralog:0.6.0 /install/scripts/setup.py
docker compose pull
docker compose up -d --wait --wait-timeout 180
docker compose exec gateway python -m montralog create-user --username admin --name Administrator
docker compose ps
```

Choose a unique password, then open **http://localhost:8080**. Browser access uses your login session. Setup creates `.env` once with distinct machine tokens, a customer identity and encryption key; an existing file is preserved. Protect that file with OS permissions, including an operator-only ACL on Windows. Never share or commit it. Root is used only for the short bootstrap container writing configuration; applications run as UID 10001.

The stack includes Prometheus, Collector, Alertmanager and background workers. Ports bind to loopback. Before remote access configure HTTPS, secure cookies and restricted ingress. Connect exporters or instrument applications to collect their data. For multiple customers, follow [customer isolation](TENANCY.md).

## Operate

```sh
docker compose ps
docker compose logs --tail 100 gateway notifications collector
docker compose stop
docker compose up -d --wait
```

Named volumes retain data. `docker compose down -v` destroys volumes. Always use the correct customer environment file on every command.

## Back up and upgrade

Preserve the original `.env`, customer identity and encryption key separately from database backups. Back up before starting a new image:

```sh
docker compose exec gateway python -m montralog backup --destination /data/pre-upgrade.db
docker compose cp gateway:/data/pre-upgrade.db ./pre-upgrade.db
```

Use a new backup filename each time. Protect the downloaded database. This backs up application SQLite data, not Prometheus or Collector volumes. PostgreSQL needs native backups/PITR. Obtain the new release source/Compose files without overwriting private configuration, then:

```sh
docker compose pull
docker compose up -d --wait --wait-timeout 180
docker compose exec gateway python -m montralog encrypt-secrets
docker compose exec gateway python -m montralog verify-secrets
```

Migration is transactional/idempotent; wrong keys abort it. Verification reads without modifying records and fails if plaintext credentials remain. Reuse the original key. For a pre-encryption installation, generate the private key file with `scripts/create_encryption_key.py` inside the helper Docker container; see [the historical key procedure](SECURITY-0.5.1.md). Supply that file to all subsequent Compose commands.

Schema 6 binds a database to `MONTRALOG_TENANT_ID` on first upgrade. Existing configurations without that variable retain identity `default`. Do not change it or mount another customer's volume. Older images reject newer schemas; rollback requires the matching old database, image and configuration.

## Restore and key loss

Restore into a separate, stopped Docker project using the original tenant ID and encryption key. Copy the database into its own application volume, assign UID/GID 10001, start it and run `verify-secrets`. Verify login, telemetry counts, dashboards and a controlled notification before switching traffic. Wrong tenant bindings are rejected.

Recover a lost active key from its separate protected backup. Without any original key copy, encrypted credentials cannot be decrypted. Preserve telemetry/accounts and have an operator re-provision integrations through a planned recovery procedure; there is no decryption bypass. Test this procedure in staging before adoption.

## Release verification

[Public reports](reports/README.md) include scan JSON, inventories, static findings, checksums, image digest, provenance and failure/recovery results. Pin the released image digest. See [production acceptance](PRODUCTION.md). Older Helm artifacts remain available for compatibility; Docker is the documented installation path for this release line.
