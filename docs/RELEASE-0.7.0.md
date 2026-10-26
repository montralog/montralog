# Montralog 0.7.0

Customer-silo assurance and optional evidence-first investigations.

- Customer-bound machine and managed tokens, database key fingerprints and customer-derived integration encryption; offline duplicate-key/project/token audit and non-destructive upgrade helper.
- Private SQLite snapshots with integrity manifests, verified restore and wrong-key/customer rejection.
- Atomic 24-hour ingestion replay receipts for native JSON and OTLP logs/traces.
- Alert state recovery across unknown source health, concurrent evaluation protection, bounded leased notification delivery and failure/restart regression tests.
- Stronger login budgets and blocked IPv4 translation/tunnel destinations; pinned local AI connections reject public DNS answers.
- Administrator investigations capture actual evidence IDs and noise counts. Optional Ollama Qwen3 4B and bounded hosted-provider adapters use durable jobs, consent and daily budgets. Model hypotheses are unverified. The only approved runbook is a read-only source recheck.

Install with Docker Compose. Existing 0.6 users must follow [ASSURANCE.md](ASSURANCE.md): preserve keys, back up with the old image, rotate machine/legacy managed tokens, migrate and verify secrets. Schema 7 is not backward compatible with an older binary. Rollback needs the old image and old backup.

Security reports and test artifacts accompany the release. The independent-agent review is not a third-party penetration test. Short controlled load tests do not establish an SLA or long-duration capacity. Live hosted model providers, enterprise identity tenants and real Slack destinations require operator-specific validation. Shared-database SaaS tenancy and privileged autonomous remediation are not provided.
