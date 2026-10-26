# Evidence-first investigations

Administrators can open **Investigations** without enabling AI. Montralog captures a bounded snapshot of log-pattern examples, changes and failed spans, shows their actual record IDs and counts repeated log patterns. This groups noise; it does not delete or automatically suppress alerts.

## Optional local model

The default optional model is Qwen3 4B through Ollama. It is a practical CPU evaluation starting point, not a claim of best accuracy. Allow roughly 6 GB of free memory plus the rest of the monitoring stack, and download the approximately 2.5 GB weights explicitly. Model licenses and hardware requirements are separate from Montralog's license.

From the repository root after the normal Docker setup:

```sh
docker compose -f compose.yaml -f deploy/docker/compose.ai.yaml up -d --wait
docker compose -f compose.yaml -f deploy/docker/compose.ai.yaml exec ollama ollama pull qwen3:4b
```

Use these same two `-f` arguments for subsequent Compose operations. Each customer project gets its own application database and model volume. Ollama exposes no host port. The application and investigation worker share that customer's database. No Docker socket is mounted. Local model requests require private destination addresses at the actual pinned connection; a public DNS answer is rejected.

Open Investigations, choose a service/window, opt into model analysis and submit. Processing is asynchronous; use Refresh to retrieve the result. An unavailable model or invalid response produces a failed job with an audit record. Jobs interrupted after a provider attempt are not silently retried, because the original request may have incurred cost.

## Other providers

The bounded adapter supports Ollama, OpenAI Responses, compatible chat-completion endpoints, Anthropic Messages and Gemini generateContent. The optional Compose file maps these settings from your private customer environment file to both gateway and investigation worker. Set: `MONTRALOG_AI_ENABLED=true`, `MONTRALOG_AI_PROVIDER`, `MONTRALOG_AI_MODEL`, `MONTRALOG_AI_URL`, and `MONTRALOG_AI_API_KEY`. Hosted providers require HTTPS, `MONTRALOG_AI_EGRESS=true` and explicit sharing consent for each investigation. Never put a provider key in the browser, repository or public report. Local HTTP is reserved for explicitly configured local Ollama.

The snapshot includes selected redacted message excerpts, service/environment names, timestamps, trace IDs and customer ID. It excludes arbitrary log attributes and configuration secrets. Redaction is best effort; classify the remaining telemetry before permitting external processing. A configured hosted endpoint may bill the operator.

The optional AI Compose file defaults to 20 submissions/day and 300,000 conservative reserved units/day per customer (the bare backend default is 100,000). A reservation counts UTF-8 prompt bytes plus the maximum 1,500 output tokens; it is an upper-bound planning allowance, not a price or invoice. Failed attempts retain their reservation. Configure `MONTRALOG_AI_DAILY_REQUESTS` and `MONTRALOG_AI_DAILY_TOKEN_BUDGET` deliberately. Responses are capped at 64 KiB. History has a 10,000-record safety ceiling.

## What a result means

Every accepted hypothesis must reference IDs in its captured evidence. The UI links those references to the snapshot. This verifies reference membership, not the truth of a model's explanation. All model conclusions remain **unverified hypotheses**, and causality is never automatically marked proven. Treat log text and model output as untrusted. Only the bounded read-only metric tools described below are available in agent mode; shell execution and automatic infrastructure changes are disabled.

The only implemented runbook is a read-only data-source health recheck. It requires an explicit proposal, typed approval, an unchanged source configuration, a five-minute approval window and a separate execution action. Every step is audited and replay is rejected. Privileged automated remediation remains a future feature requiring its own runner, permission boundaries, rollback and review.

Hosted-provider contract tests use synthetic mocked replies. The local-ai gate also downloads Qwen3 4B and performs real local inference on four synthetic cases, including untrusted log instructions and a bounded agent case. It checks JSON/citation format and records latency and token counters. These tests do not establish hosted-provider compatibility or root-cause accuracy; live credentials and deployment-specific evaluation are required before adoption.

References: [Ollama API](https://docs.ollama.com/api/chat), [Qwen3 4B](https://ollama.com/library/qwen3:4b), [OpenAI structured output](https://developers.openai.com/api/docs/guides/structured-outputs), [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create), [Gemini generateContent](https://ai.google.dev/api/generate-content).


## Agentic assistant (0.8)

The assistant uses Montralog's connected data sources directly; an MCP server is not required. There is no general-purpose MCP client or arbitrary remote tool execution in this release. Administrators choose an approved model, source, metric, question and optional alert. Dashboard panels expose **Ask AI**; alerts expose **Investigate**. Both open a side dialog while preserving the dashboard. Refresh the queued report to inspect its progress, or open the full evidence report.

The agent captures local logs, failed spans and changes, reads the selected Prometheus metric, and may request at most two follow-up snapshot/trend tools from the built-in metric catalog. Total provider calls are capped at three. It cannot choose a URL, connection credential, arbitrary PromQL, shell command, or another source. The selected source configuration is fingerprinted; changes before execution require resubmission. Source-wide metrics are explicitly labelled: service attribution is not inferred from unrelated host samples. Saved data-source credentials stay on the server and never enter the model prompt.

The result distinguishes observed evidence, unverified hypotheses, literal supporting excerpts, missing evidence and recommended read-only checks. Each hypothesis must cite captured record IDs and include an exact excerpt from the referenced message/name; fabricated references or excerpts fail validation. This checks provenance, not semantic truth or proof of causality. Missing or unavailable metrics remain missing evidence, not a zero-valued healthy measurement. A model/provider error, invalid output, repeated/unknown tool or exhausted step limit fails closed. The tool trace records the read-only inspection steps. No infrastructure remediation is performed by the agent.

Agent mode reserves **94,500 conservative units** before queueing: three calls, each at most 30,000 UTF-8 prompt bytes plus 1,500 output tokens. Requests/day counts submitted investigations, not individual model calls. Reservations are conservative and are not refunded on failure; they are not a monetary invoice. The optional AI Compose file defaults to 300,000 units/day, enough for three maximum-size agent reservations. A backend using the older 100,000 default allows one. Set `MONTRALOG_AI_DAILY_TOKEN_BUDGET` and `MONTRALOG_AI_DAILY_REQUESTS` to your approved limits. Hosted sharing consent covers bounded reads from the selected source as well as captured logs; inspect that scope before approving.

### Alert playbooks

Each alert can save a runbook context, up to eight read-only checks and recovery criteria. A linked investigation captures that alert's condition and runbook; the alert's service/environment and metric source override conflicting submitted filters. Runbooks guide analysis; text in a runbook cannot grant tools or execute commands. The existing explicitly approved source recheck remains a separate administrative action. This release starts investigations on request, not automatically on every alert transition.

### Approved model choices

Operators define `MONTRALOG_AI_PROFILES` as a private JSON object. Browser users can select these approved IDs; they cannot add arbitrary endpoints or keys. The default deployment model remains available. Example private customer environment additions:

```dotenv
MONTRALOG_AI_PROFILES='{"company":{"provider":"openai-compatible","model":"approved-company-model","url":"https://models.example.com/v1","key_env":"COMPANY_AI_KEY"},"local":{"provider":"ollama","model":"qwen3:4b","url":"http://ollama:11434","local_http":true}}'
MONTRALOG_AI_PROFILE_KEYS='{"COMPANY_AI_KEY":"REPLACE_PRIVATELY"}'
MONTRALOG_AI_EGRESS=true
```

`models.example.com` is a placeholder, not a working provider. Use your approved real endpoint/model. Protect the environment file and never publish its values. Profile keys can alternatively come from named process environment variables. The optional Compose file maps the profile/key JSON to gateway and worker; a bare host variable must be explicitly passed if you use that alternative. Restart both services after a profile change. Hosted profiles require HTTPS and per-investigation approval. Private company endpoints also need an exact `hostname:port` entry in `MONTRALOG_ALLOWED_DESTINATIONS`; this does not permit metadata/link-local endpoints. Keep default-model and profile settings consistent on gateway and worker.

Local models require the selected weights to be downloaded to Ollama. Hosted profiles support OpenAI Responses, compatible chat completions, Anthropic Messages and Gemini generateContent; their real credentials, entitlements and model behavior require operator validation. The browser receives only profile IDs, provider names and model names, never keys or endpoint credentials.

All agent metric reads use the captured investigation window, including follow-up queries. Queue delay does not silently shift the metric window away from the log snapshot. Reports reused from the cache retain their original captured window.

An agent may return **insufficient evidence** with no hypothesis. The application does not require a model to invent a cause when relevant observations are absent.

A malformed final analysis may be corrected within the same three-call cap and reservation. Invalid evidence is never displayed as an accepted hypothesis. Transport failures are not silently retried; exhausted corrections result in a failed report.

Local Ollama agent responses use [schema-constrained output](https://ollama.com/blog/structured-outputs), including allowed evidence IDs and captured excerpt choices. Other provider adapters retain server-side validation and bounded corrections; a provider/model must be evaluated for the required output contract before adoption. Schema conformance still does not prove the model's causal explanation.
