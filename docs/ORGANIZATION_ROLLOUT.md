# Organization rollout and acceptance

Use this checklist to record the evidence for your own deployment of 0.6.0. Release CI covers reproducible fixtures; your service mix and operational objectives determine acceptance in your organization.

| Area | Required organization evidence |
|---|---|
| Inventory | Release version and image digest; Linux/amd64 hosts; configuration ownership |
| Access | Individual admin/viewer accounts, HTTPS, secure cookies, least-privilege machine tokens and revocation test |
| Secrets | Authentication and encryption Secrets provisioned; private key backup; legacy credential migration completed |
| Telemetry | Representative service logs/traces and Prometheus metrics; ingestion/query counts and timestamps checked |
| Dashboards | Saved panels/timelines reopen after sign-out and restart; service/environment filters checked |
| Alerts | Real firing, pending period, resolution and destination receipt; Slack needs the operator's own webhook |
| Company login | Tenant registration, exact allowed domains, actual sign-in and provider outage behavior |
| Recovery | Separate restore rehearsal verifying telemetry, accounts, dashboards and encrypted credentials with the preserved key |
| Customer boundary | Separate Docker projects, keys, tokens, volumes and networks; reject wrong-customer sessions/tokens and verify tenant bindings |
| Capacity | Representative sustained ingestion and queries, retention/disk pressure, target latency/error budgets and overload behavior |
| Operations | Named operators, independent pipeline monitoring, private vulnerability reporting and upgrade/rollback ownership |

Deploy each customer in its own Docker stack using [tenant isolation](TENANCY.md). Teams/groups organize membership; they do not isolate telemetry or grant inherited custom roles. There is no SCIM or automatic directory deprovisioning. Microsoft 365/Google/Okta audit-event polling is not included in company sign-in. Exporter coverage depends on the sources you configure.

SQLite supports one gateway. PostgreSQL supports shared application storage across gateways; Prometheus, Collector and the singleton notification evaluator need their own availability planning. No production load guarantee is inferred from short smoke tests.

For staging test evidence, use the documented test suite and `scripts/functional_review_smoke.py`, which uses isolated temporary data. Browser tests use their own local fixture server and never read operator `.env` files. Run live workload tests only against the staging deployment you selected; keep customer data and secrets out of public issues, reports and screenshots.

See [container installation](CONTAINERS.md), [operations](OPERATIONS.md), [security upgrade](SECURITY-0.5.1.md), [production checklist](PRODUCTION.md) and [support policy](SUPPORT.md).
