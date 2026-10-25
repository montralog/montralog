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

The first Alpine candidate passed all five existing CI jobs ([run](https://github.com/montralog/montralog/actions/runs/40163198582)). Its scan identified Alpine 3.24.3, 29 OS packages and seven Python packages, with zero HIGH/CRITICAL findings. Four added browser acceptance cases passed locally using temporary synthetic data. The final release workflow repeats these checks with the complete release code and secure defaults.

The earlier RC's 44 Debian package findings remain in [the historical RC record](SECURITY_VERIFICATION-0.5.1-rc1.md). They are not suppressed in the stable scan: the runtime changed to a pinned Alpine image, and the gate now also rejects unfixed findings. Passing scan results are a time-specific observation, not proof of all future security properties or an independent audit.

Docker and Helm require an operator-held encryption key. Existing plaintext integration records require explicit migration after backup. Preserve keys separately from database backups; older versions cannot read encrypted integration fields.

Supported published container platform is Linux/amd64. Tenant SSO, actual Slack receipt, target-cluster networking/TLS, sustained workload capacity and production recovery need organization acceptance. See [rollout requirements](ORGANIZATION_ROLLOUT.md), [security upgrade](SECURITY-0.5.1.md), [support scope](SUPPORT.md) and [test instructions](TESTING.md).
