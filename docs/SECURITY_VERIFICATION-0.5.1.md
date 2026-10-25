# 0.5.1-rc1 release and security verification

Published 25 October 2026 from commit `7f37420b73ad9acaf084fd189dc06dcaa69f61e7`.

- [Immutable versioned release and assets](https://github.com/montralog/montralog/releases/tag/v0.5.1-rc1)
- [Passing release workflow](https://github.com/montralog/montralog/actions/runs/40162322456)
- [Passing Helm repository publication](https://github.com/montralog/montralog/actions/runs/40162684747)
- [Security upgrade and key preservation](SECURITY-0.5.1.md)

## What passed

All release gates succeeded: 148 Python test executions on each of Python 3.11 and 3.13 (including isolated PostgreSQL), three frontend component tests, real loopback HTTP ingestion/SQLite restoration, Docker private-file exclusion, Kubernetes SQLite/PostgreSQL deployment and restart checks, dependency auditing, high-severity static analysis and the fixable high/critical container vulnerability gate.

The encryption checks cover protected integration values, wrong/missing keys, idempotent migration, transaction rollback and OIDC regressions with encrypted configuration. A real two-server redirect test verifies that collector redirects do not transmit the ingest token to another server. Provider exchanges still use mocked tenant endpoints; this does not establish live tenant SSO.

The downloaded release assets were independently inspected after publication: all SHA-256 checksums matched; application, wheel and Helm versions agree; the wheel contains the encryption module; the tagged source excludes private env/runtime folders; and the Helm archive contains its README and license. Application `0.5.1-rc1`, Python package `0.5.1rc1`, chart `0.5.1-rc.1`, schema `5`.

## Findings and limits

The full published image report contains **44 HIGH package findings across eight distinct Debian advisories**, **zero CRITICAL findings**, and **zero high/critical findings with a fixed version listed by the scanner**. The four fixable findings in the earlier image's unused installer copies were removed by removing those runtime tools. No application Python-package high/critical findings remained in the final image scan. The resolved runtime dependency audit reported no known vulnerabilities, and the high-severity Bandit gate passed. Medium/low static findings remain in the attached full report for review; the gate does not discard that report.

These are scanner observations for the exact CI build and its vulnerability database at release time, not proof of exploitability or absence of vulnerabilities. The known unfixed OS findings are disclosed in the public release notes. The security report and dependency inventory are release assets; checksums are integrity checks, not an independent publisher signature. A public application container image is not published; operators build from the tagged source.

## Repository protections verified

Private vulnerability reporting, secret scanning, secret push protection, dependency vulnerability alerts and automatic dependency security updates are enabled. Main requires the two Python jobs, containers, Helm and security checks for non-admin contributors, with strict up-to-date checks and the existing review protections. The owner's administrator exception remains enabled as requested; force-push/deletion protections remain unchanged.

## Adoption requirements

Use the explicit encrypted-credential migration for existing plaintext records. Preserve an existing encryption key; do not generate a replacement for records already encrypted with it. Protect database and key backups separately. Read the versioned release notes before upgrading or rolling back.

Live SSO, real Slack receipt, full browser end-to-end coverage, sustained load, target-cluster hardening and production incident recovery remain operator validation work. This is a prerelease, with no independent security audit, universal production certification, tenant-isolation claim or zero-vulnerability guarantee.
