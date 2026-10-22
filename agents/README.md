# Collectors and agents

host/agent.py samples its current host/namespace using psutil. It is separate from
the gateway package; install host/requirements.txt on each host and supervise the
agent with a restricted account. Remote collection requires HTTPS.

Application SDKs send OTLP to the OpenTelemetry collector. Exporters provide
Prometheus-compatible host, container, Kubernetes and database metrics.
The collector configuration belongs in deploy/docker or the Helm chart, not in
the host agent. There is no privileged Docker-socket agent in this repository.
