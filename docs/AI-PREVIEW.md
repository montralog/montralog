# Isolated preview of the 0.8 assistant

Version 0.8 is prepared in PR #4; the published stable release remains 0.7. Use a new checkout and fresh private credentials for this preview. Do not copy a production environment file, mount its volumes, or switch an existing live stack to this branch.

```sh
git clone --branch codex/agentic-observability https://github.com/montralog/montralog.git montralog-ai-preview
cd montralog-ai-preview
docker run --rm --user 0:0 --entrypoint python -v "${PWD}:/install" ghcr.io/montralog/montralog:0.7.0 /install/scripts/setup.py
docker compose -p montralog-ai-preview -f compose.yaml -f deploy/docker/compose.ai.yaml build gateway
docker compose -p montralog-ai-preview -f compose.yaml -f deploy/docker/compose.ai.yaml up -d --wait
docker compose -p montralog-ai-preview -f compose.yaml -f deploy/docker/compose.ai.yaml exec ollama ollama pull qwen3:4b
docker compose -p montralog-ai-preview -f compose.yaml -f deploy/docker/compose.ai.yaml exec gateway python -m montralog create-user --username admin --name Administrator
```

The published 0.7 image in the helper command runs the new checkout's standalone setup script; the application itself is built from this branch and locally tagged 0.8. All application services share that locally built image. The explicit preview project name separates Docker volumes and networks. Select different HTTP/OTLP ports in the new preview `.env` if your normal stack already uses the defaults. Restrict the new private file's permissions.

In the UI, save an alert with a runbook and choose **Investigate**, or open a dashboard panel and choose **Ask AI**. Pick the model profile, source and question. Start with evidence only, then enable model analysis. Hosted profiles require explicit sharing consent; local Ollama stays on the private preview network. Refresh the queued report. Inspect quoted evidence, missing data, timestamps, source scope and read-only tool trace before acting on advice.

Follow [AI configuration](AI-INVESTIGATIONS.md) for model profiles, budgets and limits. No MCP server is required, no infrastructure commands are executed, and no automatic analysis is triggered for every alert. The assistant currently requires an administrator account. Do not infer production readiness from a successful preview.
