# Isolate customers with Docker

Montralog uses **silo tenancy**: one Compose project, gateway, database, Prometheus store, Collector queue, notification worker, credentials and encryption key per customer. No customer shares an application process or database. Teams/groups operate within a customer; they are not tenant boundaries.

## Provision a customer

From the release source folder, choose three unused local ports:

```sh
docker run --rm --user 0:0 --entrypoint python -v "${PWD}:/install" ghcr.io/montralog/montralog:0.6.0 /install/scripts/create_tenant.py --tenant acme --http-port 8180 --otlp-http-port 4418 --otlp-grpc-port 4417
docker compose --env-file .local/tenants/acme.env pull
docker compose --env-file .local/tenants/acme.env up -d --wait
docker compose --env-file .local/tenants/acme.env exec gateway python -m montralog create-user --username admin --name Administrator
```

Open `http://localhost:8180`. Repeat with a different ID and ports. Generated `COMPOSE_PROJECT_NAME` separates networks/volumes. Use the customer's `--env-file` on **every** command, including backups. The helper refuses to overwrite credentials or reuse ports assigned in another customer file. Protect `.local/tenants` and back up keys separately.

## Enforced boundaries

- Every database transaction checks its persisted tenant identity. Mounting customer A's database in B fails closed for gateways, workers and CLI commands.
- Machine tokens are generated independently; managed tokens, accounts, roles, sessions, OIDC state, dashboards, data sources, telemetry and notification queues stay in their customer's database.
- Session/OIDC cookie names include customer identity. Cross-customer sessions and machine tokens are rejected.
- Optional `X-Montralog-Tenant` must match the configured identity. It never selects a database or grants permission. Payload labels, Host and forwarded headers do not select a customer.
- `MONTRALOG_TENANCY_MODE=shared` is rejected. A shared-gateway/database SaaS mode is not implemented.

Configure a separate hostname and TLS route for each remotely accessible customer. Never reuse environment files or keys, mount another customer's volume, join data networks or expose the Docker daemon to customers. Docker host/root operators remain trusted; stronger isolation against host compromise requires separate hosts/VMs.

Tests cover database reassignment, wrong tenant headers, cross-customer tokens/sessions and separate storage/configuration. This establishes a tested silo boundary, not shared-database SaaS, billing/provisioning automation, independent security certification or HA. Follow [production acceptance](PRODUCTION.md).
