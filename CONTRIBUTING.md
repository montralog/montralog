# Contributing

Report reproducible issues with version, sanitized configuration, expected behavior
and observed behavior. Never include tokens, .env, sensitive logs or databases.

Explain the user-visible problem in each change. Add meaningful tests for ingestion,
auth, queries, correlation and recovery. Run Python tests, JS checks and Docker CI.
Document compatibility and operational changes.

Contributions use Apache-2.0 as in LICENSE. Preserve third-party notices and do not
copy incompatible code. Publish maintainer ownership, review policy and security
support window before a stable release.

## Protected main branch

Work on a feature branch and open a pull request. Main requires an up-to-date branch, one approving review, resolved review conversations, and all four GitHub Actions checks: application (3.11), application (3.13), containers and helm. Stale approvals are dismissed and the latest push needs approval by someone other than its pusher. Administrators follow the same merge requirements. Force pushes and branch deletion are disabled; history must stay linear.

An author cannot approve their own pull request. A sole maintainer needs another trusted reviewer for their own changes. Repository owners can administer protection settings; those settings are an administrative trust boundary, not an immutable guarantee.

Do not push fixes directly to main or bypass failed checks. Keep deployment credentials in protected operator settings, not pull requests.
