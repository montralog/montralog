# Public security and acceptance reports

Reports apply to their exact version/image, not every deployment. They are scan snapshots and tested scenarios, not an independent audit.

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
