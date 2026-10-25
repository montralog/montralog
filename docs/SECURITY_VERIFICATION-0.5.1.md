# Stable 0.5.1 verification

Application, Python package, Helm chart and public image tag use **0.5.1**. Schema remains **5**.

The stable release workflow requires all checks below before publication. Its reports and image digest are attached to [the versioned release](https://github.com/montralog/montralog/releases/tag/v0.5.1); use the published run and artifacts as the authoritative result for that exact source commit.

| Gate | Required coverage |
|---|---|
| Python | Python 3.11 and 3.13; SQLite/PostgreSQL functional and security regressions |
| Frontend | Dashboard renderer behavior and numeric edge cases |
| Browser | Real Chromium login/profile/logout, dashboard persistence, log escaping/search and viewer restrictions |
| Docker | Actual image build, private-file exclusions, backend configuration, OTLP and installation checks |
| Kubernetes | SQLite/PostgreSQL chart install, storage, two gateway replicas, restarts and encryption Secret wiring |
| Security | Dependency audit, static analysis and complete OS/Python image inventories; reject all HIGH/CRITICAL findings, including unfixed findings |
| Publication | Load the exact scanned image archive, match image ID/revision, test hardened startup and recovery, anonymous manifest digest match and GitHub source provenance |

## Published evidence — 25 October 2026

Stable release [v0.5.1](https://github.com/montralog/montralog/releases/tag/v0.5.1) was published from commit `6cce587175c502502412f5df222d7192fab7e6c7`. The [release workflow](https://github.com/montralog/montralog/actions/runs/40181025786) passed all six verification jobs and publication. The first publication attempt was denied by the organization's private-only package policy; after enabling public packages, the failed publishing job was rerun against the same verified commit and image archive.

- **151 Python tests passed on each of Python 3.11 and 3.13**, plus three frontend renderer tests.
- **Four Chromium acceptance tests passed**: authentication/profile/logout, saved dashboard persistence, literal log rendering/search and viewer access restrictions.
- Docker and Kubernetes verification passed, including the chart's SQLite/PostgreSQL deployment profiles, encryption Secret wiring, persistence and restart checks.
- The released image scan identified Alpine 3.24.3, 29 OS packages and seven Python packages: **zero HIGH and zero CRITICAL findings**, including unfixed findings. Dependency audit and static security checks passed.
- Publication loaded the exact scanned image archive, checked its image ID and source revision, and passed hardened startup, synthetic HTTP ingestion and backup/restore checks.
- Both `0.5.1` and `latest` were published publicly. Anonymous manifest access matched the release digest. GitHub build provenance was generated and pushed to the registry.
- All eight downloadable asset checksums were verified independently after publication. The public Helm index and downloaded chart match the release asset, and prior chart versions and Verified Publisher ownership metadata remain available.

Published image:

```text
ghcr.io/montralog/montralog@sha256:76174bb75442ab39cfd52e1d0820b7ae523f32ffd5c872b9076ea8a90902c254
```

The release includes `IMAGE_DIGESTS.txt`, `SHA256SUMS.txt`, the complete security report archive, a CycloneDX dependency inventory and the browser HTML report. The [public package](https://github.com/montralog/montralog/pkgs/container/montralog) is linked to the source repository. [Helm publication](https://github.com/montralog/montralog/actions/runs/40181837491) succeeded; install chart `0.5.1` from `https://montralog.github.io/montralog`.

Main retains six required status checks and one approving review for non-admin changes. The owner/admin exception remains enabled as requested; force pushes and branch deletion are blocked.

The earlier RC's 44 Debian package findings remain in [the historical RC record](SECURITY_VERIFICATION-0.5.1-rc1.md). They are not suppressed in the stable scan: the runtime changed to a pinned Alpine image, and the gate now also rejects unfixed findings. Passing scan results are a time-specific observation, not proof of all future security properties or an independent audit.

Docker and Helm require an operator-held encryption key. Existing plaintext integration records require explicit migration after backup. Preserve keys separately from database backups; older versions cannot read encrypted integration fields.

Supported published container platform is Linux/amd64. Tenant SSO, actual Slack receipt, target-cluster networking/TLS, sustained workload capacity and production recovery need organization acceptance. See [rollout requirements](ORGANIZATION_ROLLOUT.md), [security upgrade](SECURITY-0.5.1.md), [support scope](SUPPORT.md) and [test instructions](TESTING.md).
