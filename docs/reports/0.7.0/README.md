# Montralog 0.7.0 published evidence

[Stable release](https://github.com/montralog/montralog/releases/tag/v0.7.0) · [Successful gated workflow](https://github.com/montralog/montralog/actions/runs/40281893403) · [Binding metadata](release.json) · [Independent-agent review](security-review.md)

Image: `ghcr.io/montralog/montralog@sha256:e331ddfe4342642954f920c1af9590286275802dcbdbca8a3f8244c30c9b800a`

The release workflow scans one image, verifies its source label and identity, repeats bootstrap/load/recovery tests against that image and publishes the same image. Release assets include scan JSON, SBOM, checksums, browser results, acceptance reports and local-model evaluation. Downloaded report asset checksums were verified before copying these files.

## Results

- Python 3.11 and 3.13: 236 tests each, 234 passed and two SQLite-only backup cases skipped in PostgreSQL subclasses. SQLite backup tests ran separately in the same suite.
- Five Chromium browser tests and three renderer tests passed.
- Image scan: zero known vulnerabilities at every severity. Static scan: 28 medium B608 SQL-construction warnings and two low B105 empty-secret-default findings, preserved in [full static report](bandit-all.json); no high findings. These are distinct scan scopes.
- [Exact-image reliability test](reliability-soak.json): 30,000 unique acknowledged and stored events over 30.229 seconds; 0 missing, 0 extra after duplicate requests. Throughput 992.44 events/s at the configured 1,000 events/s target; query p95 45.678 ms. Gateway recovered in 1.247 seconds, retained all records and added no duplicates on receipt replay.
- Backup/manifest integrity, wrong-silo rejection, encrypted credential restoration, restored pending deliveries and receipts, worker-process retry recovery and firing-to-resolution delivery passed. Slack was stubbed.
- [Real Ollama Qwen3 4B evaluation](local-model.json): three synthetic format/citation cases passed, including hostile log instructions. This does not establish causal accuracy or hosted-provider compatibility.

The [independent-agent security review](security-review.md) documents findings, fixes and remaining limits. No external professional penetration-test certificate, long-duration production load claim, shared-database SaaS isolation or autonomous infrastructure remediation is claimed. Follow [deployment acceptance](../../PRODUCTION.md) and [backup/isolation instructions](../../ASSURANCE.md).
