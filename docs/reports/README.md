# Public security and acceptance reports

Reports apply to their exact version/image, not every deployment. They are scan snapshots and tested scenarios, not an independent audit.

## Published 0.6.0 evidence

Source: `ae38edd9dcdd415e53fbe61edfad62749ccfda02`. [Successful release verification](https://github.com/montralog/montralog/actions/runs/40203198912) and [immutable downloads](https://github.com/montralog/montralog/releases/tag/v0.6.0).

| Check | Result |
|---|---|
| Image scan | HIGH 0, CRITICAL 0; all severity counts and inventories retained |
| Static analysis | 0 HIGH, 18 MEDIUM, 2 LOW warnings retained |
| Python | 167 tests discovered per Python 3.11/3.13; one intentional SQLite-only backup skip in the PostgreSQL subclass |
| Browser / frontend | Four Chromium acceptance cases and three renderer tests passed |
| Bootstrap | Docker-only setup, private operator-owned files, unique customer credentials, no overwrite and invalid/overlapping configuration rejection passed |
| Ingestion | 10000 acknowledged / 10000 stored; 0 missing, 9184.86 events/s in this short synthetic run |
| Concurrent log queries | p95 112.347 ms; 20 query measurements |
| Storage failure | Explicit 503 retry and recovery passed |
| Gateway restart | 10001 before / 10001 after; recovery 1.344 seconds |
| Alert worker | Persisted queue recovered after two stubbed failures in separate worker processes |

[Release/source/image identity](0.6.0/release.json), [all-severity image scan](0.6.0/image.json), [summary](0.6.0/summary.json), [dependency audit](0.6.0/dependencies.json), [all static warnings](0.6.0/bandit-all.json), [high-severity static gate](0.6.0/bandit-high.json), [exact-image load/recovery](0.6.0/load.json), [Docker bootstrap](0.6.0/bootstrap.json).

The exact scanned release image was exercised before publication, with one CPU and 512 MiB limits. These short measurements establish correctness/recovery for this workload, not sustained sizing or a latency SLA. Slack is stubbed and retry deadlines are advanced. Static SQL warnings involve parameterized values and fixed query fragments/table names; they remain visible for review. See [security review and limits](../SECURITY-0.6.0.md) and [production acceptance](../PRODUCTION.md).

## Published 0.5.1 baseline

- [Image scan and OS/Python inventories](0.5.1/image.json)
- [Scan summary](0.5.1/summary.json)
- [Dependency audit](0.5.1/dependencies.json)
- [All static findings](0.5.1/bandit-all.json) and [high-severity gate](0.5.1/bandit-high.json)
- [Immutable release archives, checksums, dependency SBOM and browser report](https://github.com/montralog/montralog/releases/tag/v0.5.1)
- [Verification evidence](../SECURITY_VERIFICATION-0.5.1.md)

The baseline image report used a HIGH/CRITICAL output filter. It is not an all-severity report. The new pipeline retains every severity and still rejects all HIGH/CRITICAL findings, including unfixed findings.

## Docker isolation and resilience release

[CI](https://github.com/montralog/montralog/actions/workflows/ci.yml) publishes `security-reports`, `acceptance-reports` and `browser-test-report`. The [0.6.0 release](https://github.com/montralog/montralog/releases/tag/v0.6.0) attaches immutable archives, image digest, CycloneDX inventory and checksums. Final evidence identifies the source commit and image; local tests do not certify another image.

Coverage includes HTTP credentials, redirect statuses, private/metadata/invalid endpoints, DNS changes and connection pinning; tenant database/session/token boundaries; encrypted migration and wrong/lost-key restore; concurrent ingestion/query measurement, storage failure retry, gateway restart, alert queue persistence and worker-process recovery.

The load probe uses disposable Docker containers, synthetic data and stubbed Slack delivery with accelerated retry deadlines. It reports throughput, counts, latency and recovery time. Actual Slack receipt, sustained sizing, host/disk failure and live SSO remain deployment acceptance tasks. Failed probes are not passing evidence.
