# Try the 0.8 assistant in an isolated Docker stack

Version 0.8.0 is [published](https://github.com/montralog/montralog/releases/tag/v0.8.0). Use a fresh checkout and private credentials for an isolated evaluation. Preserve production configuration and volumes separately.

```sh
git clone --branch v0.8.0 --depth 1 https://github.com/montralog/montralog.git montralog-ai-preview
cd montralog-ai-preview
docker run --rm --user 0:0 --entrypoint python -v "${PWD}:/install" ghcr.io/montralog/montralog:0.8.0 /install/scripts/setup.py
docker compose -p montralog-ai-preview -f compose.yaml -f deploy/docker/compose.ai.yaml pull
docker compose -p montralog-ai-preview -f compose.yaml -f deploy/docker/compose.ai.yaml up -d --wait --wait-timeout 180
docker compose -p montralog-ai-preview -f compose.yaml -f deploy/docker/compose.ai.yaml exec ollama ollama pull qwen3:4b
docker compose -p montralog-ai-preview -f compose.yaml -f deploy/docker/compose.ai.yaml exec gateway python -m montralog create-user --username admin --name Administrator
```

The explicit project name separates named volumes and networks. Before startup, choose different HTTP/OTLP ports in the new private `.env` if another stack uses the defaults. Keep the same project name, environment and two Compose files on subsequent commands. Allow roughly 6 GB free memory for the model in addition to the monitoring stack; CPU investigations can take minutes.

Save an alert with a runbook and choose **Investigate**, or choose **Ask AI** from a dashboard panel. Select a model profile, source and question. Start with evidence only, then enable model analysis. Hosted profiles require explicit sharing consent. Local Ollama stays on the private network. Refresh the queued report and inspect the captured window, citations, missing evidence and read-only trace.

Follow [AI configuration](AI-INVESTIGATIONS.md) for profiles, keys and budgets. No general-purpose MCP client, arbitrary shell tools or autonomous infrastructure changes are implemented. The assistant requires an administrator account. A successful evaluation is not production certification; use [deployment acceptance](PRODUCTION.md).
