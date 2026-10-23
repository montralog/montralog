# Verification evidence

Current public preview: **0.5.0-rc1**.

- [Executed functional review — 23 October 2026](FUNCTIONAL_REVIEW-2026-10-23.md)

- [Access and identity verification](ACCESS_VERIFICATION.md): current access/identity tests, database migration and local application checks.
- [Previous 0.4 connection verification](VERIFICATION-0.4.md): historical source-connection checks.
- [Production-readiness checklist](PRODUCTION.md): deployment-specific checks still required.

Local testing and CI runs are separate evidence. Check the repository Actions page for the actual status of hosted CI. Token tests with local signing keys and mocked provider exchanges do not establish successful live tenant sign-in. Helm rendering does not substitute for testing on a target Kubernetes cluster. No independent security audit, universal integration claim, capacity guarantee or HA certification is implied.
