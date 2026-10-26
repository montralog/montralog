# Montralog 0.8.0

Read-only agentic observability and dashboard assistance.

- Ask AI from a dashboard panel or investigate an alert without leaving the current workspace.
- Select an operator-approved model profile, connected metric source and diagnostic question.
- Capture alert conditions and saved runbooks alongside logs, traces and changes.
- Allow bounded snapshot/trend inspection from approved metrics: at most three model calls, no arbitrary URLs/queries or infrastructure execution.
- Require valid evidence IDs, literal excerpts and explicit missing evidence in agent reports. Conclusions remain unverified hypotheses.
- Preserve source fingerprints, hosted-sharing consent, private credentials, user-owned reports and conservative budgets.
- Fix the alert editor's undefined source reference and make metric alerts honor the selected saved source.

Docker Compose is the supported installation path. Use the optional AI Compose file and [AI guide](AI-INVESTIGATIONS.md) for profiles, weights, budgets and hosted consent. The optional file's default daily reservation budget is now 300,000 units; explicitly configure your own approved limit. Database schema remains 7. Keep gateway and AI worker on the same version and drain queued investigations before rollback. Existing 0.7 customer identities, tokens and encryption keys must be preserved; older installations must first follow [ASSURANCE.md](ASSURANCE.md).

The release does not implement a general-purpose MCP client, automatic investigations on alert transitions, privileged autonomous remediation or external professional penetration-test certification. Literal citation checks do not prove the model's causal explanation. Live hosted providers and deployment-specific production acceptance remain operator responsibilities.
