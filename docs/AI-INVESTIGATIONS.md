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

The bounded adapter supports Ollama, OpenAI Responses, compatible chat-completion endpoints, Anthropic Messages and Gemini generateContent. Configure the same private environment values on gateway and investigation worker: `MONTRALOG_AI_ENABLED=true`, `MONTRALOG_AI_PROVIDER`, `MONTRALOG_AI_MODEL`, `MONTRALOG_AI_URL`, and `MONTRALOG_AI_API_KEY`. Hosted providers require HTTPS, `MONTRALOG_AI_EGRESS=true` and explicit sharing consent for each investigation. Never put a provider key in the browser, repository or public report. Local HTTP is reserved for explicitly configured local Ollama.

The snapshot includes selected redacted message excerpts, service/environment names, timestamps, trace IDs and customer ID. It excludes arbitrary log attributes and configuration secrets. Redaction is best effort; classify the remaining telemetry before permitting external processing. A configured hosted endpoint may bill the operator.

Defaults are 20 submissions/day and 100,000 conservative reserved units/day per customer. A reservation counts UTF-8 prompt bytes plus the maximum 1,500 output tokens; it is an upper-bound planning allowance, not a price or invoice. Failed attempts retain their reservation. Configure `MONTRALOG_AI_DAILY_REQUESTS` and `MONTRALOG_AI_DAILY_TOKEN_BUDGET` deliberately. Responses are capped at 64 KiB. History has a 10,000-record safety ceiling.

## What a result means

Every accepted hypothesis must reference IDs in its captured evidence. The UI links those references to the snapshot. This verifies reference membership, not the truth of a model's explanation. All model conclusions remain **unverified hypotheses**, and causality is never automatically marked proven. Treat log text and model output as untrusted. No model tools, shell execution or automatic infrastructure changes are enabled.

The only implemented runbook is a read-only data-source health recheck. It requires an explicit proposal, typed approval, an unchanged source configuration, a five-minute approval window and a separate execution action. Every step is audited and replay is rejected. Privileged automated remediation remains a future feature requiring its own runner, permission boundaries, rollback and review.

Provider contract tests use synthetic mocked replies. They do not establish real hosted-provider compatibility or model quality; live credentials and deployment-specific evaluation are required before adoption.

References: [Ollama API](https://docs.ollama.com/api/chat), [Qwen3 4B](https://ollama.com/library/qwen3:4b), [OpenAI structured output](https://developers.openai.com/api/docs/guides/structured-outputs), [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create), [Gemini generateContent](https://ai.google.dev/api/generate-content).
