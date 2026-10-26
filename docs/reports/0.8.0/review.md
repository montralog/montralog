# Agentic assistant review scope

The new assistant is bounded and read-only. Existing customer-silo isolation, connection validation, DNS pinning, TLS checks, encryption and administrator/session/CSRF controls remain in effect. It uses existing saved Prometheus sources; no general-purpose MCP transport is implemented.

A separate agent performed a partial review and identified two issues: the initial maximum reservation exceeded the old default daily budget, and linked alert condition strings were not redacted before entering model context. Both were fixed. Targeted tests now cover the usable default reservation and redaction of alert service labels. The reviewer then hit a usage limit, so this is explicitly **not a completed independent review** of all new code. It is not an external professional penetration test.

Additional implementation checks enforce source fingerprints, per-step role/egress/provider revalidation, literal evidence excerpts, a three-call ceiling, no arbitrary query or URL tools, private operator-approved model keys and per-user report ownership. Regression tests reject invented excerpts, unapproved tools, changed sources, repeated tools, exceeded call limits and authorization revoked during a run. The UI escapes model/evidence output.

Remaining limits: citations do not prove causality; redaction is heuristic; source-wide metrics do not automatically establish service attribution; hosted-provider compatibility is contract-tested with mocks unless the operator validates real credentials. Budget reservations are conservative and are not an invoice. Source/worker failure produces a failed analysis, not autonomous retries or remediation. The release gates must bind the tests/scans to the exact source and published image.
