# Montralog 0.8.0 published evidence

[Stable release](https://github.com/montralog/montralog/releases/tag/v0.8.0) · [Successful gated workflow](https://github.com/montralog/montralog/actions/runs/40376265345) · [Binding metadata](release.json) · [Partial separate-agent review](review.md)

Source: `3c7a4bfcf598577c07ff69565ed05c3f338828ec`.

Image: `ghcr.io/montralog/montralog@sha256:1bd18840968c3e01eb833a83c6ab53ace48e5ea3096be35e1edd04863aa8d555`.

The workflow scanned one image, checked its source label, ran bootstrap/load/recovery against that image and published it. All ten downloaded assets matched the published SHA-256 checksums before these reports were copied. [Checksums](SHA256SUMS.txt) apply to the original release assets, not extracted report files. The release also carries the browser report, SBOM and build provenance.

## Results

| Check | Measured result |
|---|---|
| Python 3.11 and 3.13 | 282 discovered per version; 280 passed, two SQLite-only backup cases intentionally skipped in PostgreSQL subclasses |
| Browser / renderer | Seven Chromium tests and three renderer tests passed |
| Image scan | Zero known vulnerabilities at every severity in this scanner snapshot |
| Static scan | Zero high, 28 medium B608 and two low B105 warnings, retained in full |
| Exact-image ingestion | 30,000 acknowledged / stored; zero missing and zero extra after duplicate requests |
| Workload | 30.132 seconds, 995.61 unique events/s against a 1,000 events/s target; one CPU / 512 MiB |
| Concurrent log queries | p95 7.326 ms across 118 measurements |
| Restart / replay | Recovery 1.507 seconds; all 30,000 retained; zero duplicates added on replay |
| Backup / alerting | Wrong-silo rejection, encrypted restoration, pending deliveries and receipts restored; worker-process recovery and firing-to-resolution delivery passed |
| Real local model | Four synthetic Qwen3 4B cases passed; bounded-agent case 75.52 seconds with valid IDs and literal excerpts |

[Image inventory/scan](image.json) · [summary](summary.json) · [dependency audit](dependencies.json) · [full static findings](bandit-all.json) · [high-severity static gate](bandit-high.json) · [bootstrap](bootstrap.json) · [load/recovery](load.json) · [reliability workload](reliability-soak.json) · [real-model evaluation](local-model.json).

## Interactive local demo

[Sanitized demo analysis and tool trace](local-demo.json) records a separate live local run on the same source, with actual synthetic exporter → Prometheus queries and real Ollama inference. The first model request failed; the alert-linked request later completed. It captured 24 error logs, a deployment and a failed span, inspected CPU, memory and container CPU, and produced two unverified hypotheses with literal excerpts and explicit missing database evidence. No infrastructure action was executed and no hosted provider received data. This is supplementary functional evidence, not the release's performance benchmark.

## Limits

The new agent's separate review was partial; it is not an external professional penetration test. Automated scanners identify known classes, not proof of application security. Citations validate provenance, not causal correctness. The CI model case uses a synthetic metric fixture; model inference is real. The interactive demo uses live synthetic Prometheus data.

Slack delivery was stubbed and retry deadlines advanced. The 30-second SQLite test is not sustained capacity, PostgreSQL failover, disk/host failure, whole-stack HA or a latency SLA. Live SSO, Slack receipt, hosted-model compatibility and deployment acceptance require operator verification. Customer isolation is separate Docker stacks, not shared-database SaaS. See [production acceptance](../../PRODUCTION.md).
