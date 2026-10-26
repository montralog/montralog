# Montralog 0.7.0 independent-agent security review

Review date: 2026-10-26. Target: the local `codex/assurance-ai-investigations` working changes, following released commit `ae38edd9dcdd415e53fbe61edfad62749ccfda02`. Changes remained in progress during review; this report is not a signed attestation of a final release digest.

## Independence and scope

A separate AI reviewer inspected source and performed adversarial fixture tests independently from the implementation agents. This is **not an external professional penetration test, security certification, or proof that the application is secure**. No customer data, operator environment files, live provider APIs, external targets, or production databases were used. Application source was not modified by the reviewer.

Reviewed authentication, authorization and administrative APIs, outbound endpoint/credential handling, ingestion validation and retry receipts, silo identity and secret encryption, SQLite backup/restore, and evidence investigations/model providers/diagnostic runbooks. Review included selected browser rendering source; it did not include a full browser penetration assessment.

## Findings and remediation verification

| Finding | Original impact | Current evidence |
| --- | --- | --- |
| Username variation bypassed login rate limiting | P1 availability: unauthenticated callers could repeatedly trigger expensive password verification | Atomic source, account and global pre-verification budgets added. Independent fixture: 35 distinct usernames from one source produced 30 unauthorized responses, five throttles and exactly 30 verifier calls. Regression suite now covers the limit. |
| Backend unknown state lost known firing state | P1 operational reliability: missing resolution notification or duplicate firing transition | `last_known_state` and transactional state/outbox changes inspected. Original isolated firing/unknown/normal reproduction established missing resolution. Final reliability evidence must also include the dedicated notification suite and deployment failure tests. |
| Backup files were created with unsafe default semantics | P2 local confidentiality/integrity | Exclusive creation and private file mode, manifest checks, decryptability checks and restore guards added. Independent fixtures confirmed round-trip digest, wrong tenant/key rejection, existing-file preservation and cleanup after manifest collision. |
| IPv4 translation could bypass metadata destination classification | P2 conditional SSRF on hosts with a usable NAT64 route | NAT64/tunnel destinations rejected. Mock DNS reproduction confirmed rejection; no metadata endpoint or NAT64 network was contacted. |
| Local-only AI preflight resolved separately from actual connection | P2 privacy-policy bypass if DNS changed from private to public | Single connection-time resolution with `require_private` added. Independent mocked check rejected public DNS with zero sockets; private DNS used one resolution and one socket. |
| Model call failures initially lacked durable attempt history | Cost and auditability gap | Provider work now requires a durable queued record; the worker records an attempt and stores sanitized failed status. Invalid citation regression leaves a failed run and attempt audit. |
| Long tenant prefix could satisfy token length without randomness | Conditional weak manually configured machine tokens | Strict token validator now requires a 43–128 character URL-safe suffix after the exact tenant/scope prefix. Generated tokens use strong randomness. |
| Reapproving completed runbook returned misleading approval | Lifecycle/audit correctness | Conditional update count now rejects approval replay with 409. Execution remains separately claimed and requires matching owner, approval, expiry and source fingerprint. |

## Current controls observed

Administrative investigation and runbook endpoints enforce administrator role and CSRF; report access is scoped to the requesting user. Model endpoint, model name and credentials are operator configuration, not request parameters. Hosted egress requires operator opt-in plus explicit request confirmation, and the worker rechecks policy and administrator role. Local HTTP is narrowly opted in and constrained at actual connection resolution. Outbound sockets pin numeric resolved addresses, preserve TLS hostname verification, reject redirects and restrict private destinations. A total socket deadline now closes the active connection after the request budget; DNS remains subject to the operating-system resolver timeout.

Model input is capped, selected telemetry with heuristic redaction. Output citations must name supplied evidence; returned text remains an unverified hypothesis with causality explicitly unproven. UI output is escaped. There are no model tools, shell execution, or automatic infrastructure modifications. The only runbook is a reviewed read-only connection diagnostic. Atomic request/token reservations bound configured calls, including failed attempts; these are not monetary billing guarantees for arbitrary provider pricing/token accounting.

Silos use a database tenant binding, encryption-key fingerprint, tenant/scoped machine tokens and tenant-derived v2 integration encryption. A separate helper audits duplicate keys/tokens/ports across supplied deployment configurations. This is separate Docker-stack isolation under a trusted operator; it is not a shared-database customer authorization design or isolation against a hostile Docker host administrator. Legacy encryption is readable for migration and needs explicit migration/verification.

## Reproducible test evidence

The reviewer ran the following focused unittest modules using Python 3.14, disposable SQLite fixtures and mocked provider/network interactions: `test_investigations`, `test_assurance`, `test_silo_config`, `test_secret_store`, `test_outbound`. Result: **39 tests passed in 47.178 seconds**. An additional focused rerun of assurance/outbound/silo configuration passed **18 tests in 3.902 seconds**. Fixtures used a writable review workspace, not the operator database. An initial invocation lacked `MONTRALOG_TEST_TMP` and failed on restricted temporary-directory creation; the correctly configured run above passed.

Independent earlier fixtures also verified cross-tenant v2 ciphertext rejection with the same master key, backup wrong-key/tenant failures and preservation of existing destination/manifest files. Windows execution does not establish Linux ownership/mode behavior; Linux CI must verify the POSIX backup protections.

## Remaining hardening and acceptance limits

1. **Low, offline privacy hardening:** retry receipts currently persist SHA-256 of the raw ingestion body. A database reader can dictionary-test predictable bodies containing low-entropy values that log redaction otherwise removes. Consider a tenant-keyed HMAC; preserve distinct-raw-body conflict detection. This is not an unauthenticated HTTP disclosure.
2. **Low, quota accounting:** AI budget reservation and queued-record insertion are separate transactions. A database error or history-capacity race can consume quota without creating a queued run. No paid call occurs without a durable run. Reserve quota and queue atomically, or document/reconcile conservative reservations. Concurrent cache misses may intentionally use more than one bounded reservation.
3. Backup SHA-256 manifests detect corruption, not malicious replacement of both snapshot and manifest. Protect backup storage and keep recoverable encryption keys separately. Lost keys cannot be cryptographically recovered. Legacy raw snapshots need a documented compatible restore/upgrade path; the new manifest format is not universal backwards compatibility.
4. Redaction is heuristic and cannot guarantee removal of every secret, personal datum or proprietary log value. Hosted-provider confirmation must be treated as a real data-sharing decision. Citation validity does not establish that a model's causal interpretation is correct.
5. No live third-party identity-provider/provider compatibility, Slack delivery, Kubernetes or cloud metadata penetration, sustained production load, or external professional assessment was performed by this reviewer. PostgreSQL concurrency and Linux container acceptance require their own evidence. Notification delivery retains at-least-once semantics; a crash after remote acceptance can duplicate a message.
6. Before a production assurance claim, bind published scan results, regression results, load/failure measurements and this review to the final commit and image digest, and commission an authorized external penetration assessment against an isolated representative deployment.

No additional high-severity exploitable issue was demonstrated in this focused rereview. That statement describes the inspected scope and fixtures, not an assurance that undiscovered vulnerabilities are absent.

## Follow-up hardening after review

The implementation now uses a master-keyed HMAC for raw ingestion receipt bodies instead of an unkeyed digest. The independent review above describes its reviewed snapshot; the final CI checks must validate this follow-up change. Quota reservation and job insertion remain separate conservative operations, so a storage failure can consume quota without a provider request.

## Targeted final follow-up: 4f778871384a0671dc9a36fc5b1aa9d26e20749a

The independent reviewer inspected the raw ingestion receipt change to HMAC-SHA256 using the deployment master key, and the total outbound socket deadline. With a configured private production key, the receipt change addresses remaining hardening item 1 above while preserving identical-body replay and different-body conflict behavior. At this commit, an explicitly empty encryption-key environment value does not select the ingest-token fallback; encryption-disabled configurations should use a nonempty private fallback. This does not bypass the required-key production configuration.

The reviewer reran the HTTP receipt regression plus the delivery reliability module: **12 tests passed in 6.023 seconds**, including the loopback slow-drip response deadline regression. The initial restricted execution could not connect to its temporary loopback server; the permitted local-only rerun passed. This verifies actual interruption of a slow response in that fixture, alongside the inspected timer and remaining-connect-budget implementation. DNS remains governed by the operating-system resolver timeout. No live external destination or provider was contacted by this follow-up. Reported real-model and PostgreSQL CI evidence was not independently rerun here. Remaining hardening item 2 and the acceptance limits above still apply.

Subsequent working-tree correction after 4f778871: the empty-key fallback now uses the private ingest token when the master-key environment value is blank. The independent reviewer inspected the correction and reran the strengthened explicit-blank-key HTTP regression: one test passed in 0.188 seconds, including rejection of the empty-key HMAC digest. The fallback caveat in the preceding paragraph is therefore resolved in this working tree; final release evidence must identify the commit containing this correction.
