# Local Docker and Windows host collection

This agent reads `docker stats` from the selected local Docker context and sends
authenticated OTLP HTTP JSON metrics to Montralog's existing collector. Prometheus
scrapes that collector; the gateway queries Prometheus for the dashboard charts.
It does not mount the Docker socket into a web service or expose new network ports.
It collects resource usage, container names and IDs, and the machine hostname.
It does not collect container logs, environments, process command lines or files.

## Windows

From the project directory after starting Docker and Montralog:

```powershell
.\scripts\windows\Start-Local-Metrics.ps1
.\scripts\windows\Stop-Local-Metrics.ps1
```

Start is idempotent. It runs a hidden Python process, records its PID in `.local`,
and installs psutil 7.0.0 into `.local/python` if needed for host measurements.
No scheduled task or Windows service is installed. Run Start-Local-Metrics.ps1
again after reboot or sign-in. Docker restarts are retried with bounded backoff.
Agent logs rotate at 2 MiB, retaining three previous files. Startup errors are in
`.local/metrics-agent-error.log`. Runtime/dependency files are excluded from Git,
Docker build context and release source archives.

Open Dashboards in Montralog. The local installation has two saved views:

- **Local Docker · Live containers**: current table, container count, CPU,
  memory, memory limit use, process counts, network totals and agent freshness.
- **Windows host · Live resources**: Windows CPU, memory, system disk and
  agent freshness. These host figures describe Windows, not the Docker Linux VM.

Each collection occurs about every 15 seconds, plus up to one collector batch
and scrape interval before it is visible. Open saved dashboards refresh every
15 seconds. The dashboard builder itself does not auto-refresh while editing.

## Manual / other operating systems

Python 3.11+, the Docker CLI and access to the local daemon are required. Host
measurements additionally require `pip install psutil==7.0.0`.

```text
python agents/docker/agent.py --env-file .env --host --once
python agents/docker/agent.py --env-file .env --host --interval 15
```

Omit `--host` to collect only Docker, without psutil. The agent accepts local Unix
sockets or Windows named pipes, and rejects remote TCP/SSH Docker contexts. It
supports up to 100 running containers per local daemon. The default collector is
http://127.0.0.1:4318. Remote collector endpoints require HTTPS.

## Measurement semantics

Docker CPU percentage is converted to core equivalents by dividing by 100; this
is not a percentage of total host capacity. Memory percentages are relative to
the Docker-reported container limit. Byte values are approximate because the CLI
formats them with limited precision. Network and block I/O are cumulative totals,
not bytes per second. Container restarts can reset totals and change IDs.

Only running containers have resource samples. Recently stopped/replaced
containers can remain visible for up to 60 seconds; historical charts retain
older points in the selected window. Freshness guards drop obsolete local
measurements from current Prometheus evaluations after 60 seconds. The collector
itself normally keeps inactive series for its default five-minute expiry, so the
freshness chart also helps distinguish missing updates from healthy collection.

This is local resource monitoring. Application logs/traces still need an SDK or
log integration; Kubernetes pod state needs a cluster and kube-state-metrics.

References: [Docker stats](https://docs.docker.com/reference/cli/docker/container/stats/),
[Collector Prometheus exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/prometheusexporter).
