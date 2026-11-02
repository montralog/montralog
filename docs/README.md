# Montralog documentation

Start with the [Docker quickstart](../README.md#quickstart-docker). See [0.8.1 release notes](RELEASE-0.8.1.md) for dashboard features and schema-8 upgrade steps. The [release page](https://github.com/montralog/montralog/releases) determines publication status. Versioned reports only describe their stated revision and workload.

## Install and operate

| Goal | Guide |
|---|---|
| Install, upgrade and restore | [Docker installation](CONTAINERS.md) |
| Walk through a first evaluation | [Evaluation](EVALUATION.md) |
| Run day-to-day operations | [Operations](OPERATIONS.md) |
| Separate customer installations | [Customer isolation](TENANCY.md) |
| Understand storage and migrations | [Storage](STORAGE.md) |
| Protect secrets and recover backups | [Assurance](ASSURANCE.md) |
| Plan an organization rollout | [Rollout and acceptance](ORGANIZATION_ROLLOUT.md) |
| Check supported deployment scope | [Support policy](SUPPORT.md) |

## Use the workspace

- [Dashboard cards, panels, queries, themes, alerts and notifications](STUDIO.md)
- [Configure an approved AI model](../README.md#configure-your-ai-model)
- [Investigation evidence, runbooks and provider limits](AI-INVESTIGATIONS.md)
- [Data connections](CONNECTIONS.md)
- [Local accounts and sessions](ACCOUNTS.md)
- [People, teams and company sign-in](IDENTITY.md)
- [Telemetry ingestion API](API.md) and [agents](../agents/README.md)
- [Screenshot provenance and feature status](assets/screenshots/README.md)

## Develop and assess

- [Architecture](ARCHITECTURE.md) and [project structure](PROJECT_STRUCTURE.md)
- [Testing](TESTING.md) and [contributing](../CONTRIBUTING.md)
- [Public scan and verification reports](reports/README.md)
- [Dashboard creation verification](reports/dashboard-creation/README.md)
- [Published 0.8.0 evidence](reports/0.8.0/README.md), [release notes](RELEASE-0.8.0.md) and [agent review scope](reports/0.8.0/review.md)
- [Production acceptance matrix](PRODUCTION.md)
- [Release status](RELEASE.md), [changelog](CHANGELOG.md) and [security policy](../SECURITY.md)

## Historical reference

These guides remain useful for their named versions; they are not current release certifications.

- [0.6.0 security changes](SECURITY-0.6.0.md) and [release notes](RELEASE-0.6.0.md)
- [0.5.1 verification](SECURITY_VERIFICATION-0.5.1.md)
- [Functional review — 23 October 2026](FUNCTIONAL_REVIEW-2026-10-23.md)

Docker Compose is the supported installation path for new deployments. Historical Helm/Kubernetes guides and versioned artifacts remain for compatibility.
