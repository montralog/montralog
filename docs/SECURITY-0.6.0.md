# Security and upgrade — 0.6.0

Use the [Docker upgrade and recovery guide](CONTAINERS.md). Back up data and preserve the original encryption key and tenant identity before starting a new image. Schema 6 rejects downgrade and binds the database to its customer. Existing installations without a configured tenant ID bind to `default`; do not assign a new customer ID to an already-bound database.

## Outbound credential and SSRF controls

Saved Basic/bearer credentials require HTTPS with certificate verification. Changing an endpoint requires re-entering its credential; blank edits cannot forward an existing hidden credential to a different endpoint. All resolved DNS answers are validated and the socket connects to a validated numeric address, preserving the original TLS hostname. Redirects and environment proxies are disabled. Private destinations require exact operator approval through `MONTRALOG_ALLOWED_DESTINATIONS=hostname:port`; metadata, link-local, multicast and unspecified addresses remain forbidden. Only approve DNS names and services you control.

Slack and OIDC requests use the same pinned transport plus provider-specific HTTPS endpoint restrictions. The operator-configured Collector has an explicit HTTP exception inside the private Docker network. That exception cannot be selected by saved data sources or API input. Keep tenant networks isolated and do not expose internal services remotely.

## Customer boundaries

[Separate customer stacks](TENANCY.md) provide database, process, network, queue, token and key separation. Every transaction checks its stored customer identity. Browser/OIDC cookies include that identity. Tenant labels, Host/forwarded headers and request bodies cannot select a database. Shared application/database hosting is rejected. Host/root administrators remain trusted.

## Encrypted credentials and recovery

Docker requires an operator-held encryption key. `encrypt-secrets` converts legacy plaintext transactionally and validates existing ciphertext; a wrong key rolls back the operation. `verify-secrets` is read-only and rejects wrong/lost keys or remaining plaintext. Regression tests cover fresh/legacy data, idempotence, encrypted SQLite backup restoration and restoration with the original separately preserved key. PostgreSQL native backup/restore remains deployment acceptance.

There is no backdoor for an irretrievably lost key. Recover the original key from its protected backup or re-provision integration credentials through an operator recovery procedure. Encryption protects integration credentials, not telemetry, entire databases or backup files.

## Public evidence and remaining risk

[Public reports](reports/README.md) retain all image severities, package inventories, dependency audit, all static warnings, browser results and measured Docker bootstrap/load/failure evidence. HIGH/CRITICAL image findings are release blockers, including unfixed findings; no advisory is ignored to obtain a pass. Scanner results are time-specific, not independent certification.

Static SQL-construction warnings remain visible. Reviewed queries bind user values as parameters; interpolated table/field names, filter clauses and database-specific fragments come from fixed code paths. Empty-string credential defaults are not embedded production passwords. Retaining these warnings does not certify future query changes; regression and manual review remain necessary.

Validate HTTPS ingress, egress, customer registrations, actual notification receipt, sustained capacity, disk/host failure, key backups and restore procedures before production adoption. See [the acceptance matrix](PRODUCTION.md).
