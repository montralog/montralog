# Architecture

Browser → authenticated WSGI gateway → SQLite or PostgreSQL logs/spans/samples/events.
Browser → fixed gateway queries → Prometheus metrics and alert state.
OTLP clients → authenticated Collector → JSON log/trace adapter, or Prometheus
exporter → Prometheus scrape/rules → Alertmanager.

The gateway uses Python standard-library code. Gunicorn serves Docker deployments;
wsgiref is preview-only. SQLite WAL supports a single-node pilot; PostgreSQL
supports replicated gateways. Result counts and query time are bounded, but
large queries can still be expensive.

Service/environment establish correlation. Trace IDs connect logs and spans;
deployment events share those filters/time windows. Parent IDs are retained,
but the initial view sorts spans by timestamp rather than building a nested tree.
Partial sampling, clock skew and filters can produce incomplete traces.

Automatic dashboards are observed-service views plus fixed infrastructure templates.
Arbitrary log-to-dashboard interpretation, custom panel editing, parser previews
and versioned dashboard configuration remain roadmap.

No external language-model calls or automatic remediation occur. Pattern grouping
normalizes numbers/IDs and ranks error groups. It provides evidence, not causal proof.
Untrusted text is HTML-escaped and IDs validated; scripts/assets stay local.

## Next milestones

1. Container CI, SDK interoperability and pilot benchmarks.
2. Pipeline monitoring, rate limits, queue-failure qualification and log idempotency.
3. Partitioned storage, future schema migrations and refined query budgets.
4. OIDC, per-user roles, scoped service credentials and audits.
5. Tested Kubernetes deployment/discovery and Docker log integrations.
6. Dashboard editing/template detection and hierarchical trace investigation.
7. HA/recovery qualification and supported upgrade policy.

## Upstream references

- https://opentelemetry.io/docs/specs/otlp/
- https://github.com/open-telemetry/opentelemetry-collector/blob/v0.161.0/exporter/otlphttpexporter/README.md
- https://prometheus.io/docs/prometheus/latest/configuration/configuration/
- https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/
- https://prometheus.io/docs/alerting/latest/configuration/
