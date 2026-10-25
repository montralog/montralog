# Security work in 0.5.1-rc1

## Stored integration credentials

New `scripts/setup.py` installations generate an encryption key. When `MONTRALOG_ENCRYPTION_KEY` is configured, new Prometheus passwords/tokens, Slack webhooks and OIDC client secrets are stored using authenticated Fernet encryption. Password hashes and API-token hashes remain hashed as before. This feature does not encrypt telemetry, user profile fields, entire databases or existing backup files.

The key stays outside the database. Keep it in an operator-controlled secret store, restrict process/environment and backup access, and preserve it separately from database backups. Someone with both key and database can decrypt credentials. Losing the key makes encrypted credentials unusable. Rotation requires a controlled re-encryption procedure; simply replacing the key is not supported.

Existing installations without a key retain compatibility with plaintext integration records. Configuring a key encrypts new writes; it does not silently rewrite existing rows. With `MONTRALOG_ENCRYPTION_REQUIRED=true`, missing or invalid key configuration fails gateway startup. Wrong-key/tampered ciphertext fails closed and is not sent to providers.

## Upgrade existing Docker installations

1. Back up the database and keep the existing credentials secure. Review [release notes](RELEASE.md).
2. Build the new image from the `v0.5.1-rc1` tag.
3. If an encryption key is already configured, reuse it. Generate the separate private key file below only when enabling encryption for the first time; do not replace a key that already protects stored credentials:

```sh
python scripts/create_encryption_key.py --destination .local/encryption.env
docker compose --env-file .env --env-file .local/encryption.env build gateway
docker compose --env-file .env --env-file .local/encryption.env up -d --wait
docker compose --env-file .env --env-file .local/encryption.env exec gateway python -m montralog encrypt-secrets
```

Use both env files for subsequent Compose operations. All gateway and notification processes must use the same key. The migration is transactional and idempotent: it validates existing ciphertext, and aborts rather than partially migrating if the key is wrong. It prints only the count changed. Older backups may still contain plaintext and require protected retention/disposal.

## Kubernetes

Provision an operator-managed Secret and set `encryption.existingSecret` and `encryption.key`. Never put the key into Helm values or source control. The production example expects Secret `montralog-encryption` with key `encryption-key`.

Alternatively use the private env file generated above:

```sh
kubectl -n observability create secret generic montralog-encryption --from-env-file=.local/encryption.env
```

In that case set `encryption.key=MONTRALOG_ENCRYPTION_KEY`. Set the existing Secret on installation/upgrade, then run `python -m montralog encrypt-secrets` inside a gateway with the same environment. Back up and validate restoration first. Preserve the Secret across upgrades.

## Image and dependency checks

The Docker context excludes private env variants, keys, certificates, local cloud/SSH credentials, databases and logs. CI builds with disposable private-file sentinels and checks that the resulting image does not contain them. The official Python 3.13 slim base is pinned by digest. The runtime image removes pip, setuptools, wheel and ensurepip after installing application dependencies; build tools and their vendored copies are unnecessary in the immutable application runtime. Do not install packages inside running containers; rebuild the image instead.

CI runs pip-audit against resolved runtime requirements, Bandit with a high-severity gate, and Trivy against the built image. The full high/critical image report is retained; the release gate rejects high/critical findings with available fixes. Unfixed findings remain visible for operator review, and passing these checks is not an independent audit or proof of absence of vulnerabilities. Static medium findings from parameterized SQL construction and URL forwarding are retained as review considerations; the SQL parameters and forwarding destination restrictions require continued review.

## Still outside this preview's guarantees

No tenant isolation, custom RBAC, general ingestion rate limiter, tamper-proof audit log, independent security audit or HA guarantee. Deploy behind HTTPS, restrict network and database access, and perform exact-image and target-environment review. Live SSO and Slack destination validation remain deployment-specific. See [the security policy](../SECURITY.md) and [production checklist](PRODUCTION.md).
