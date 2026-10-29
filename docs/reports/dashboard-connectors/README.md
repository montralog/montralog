# Advanced dashboard and source-adapter evidence

Development implementation: `cde45b3`, tested locally on 29 October 2026.
These are synthetic functional checks, not production throughput, security
certification, an external penetration test, or support for every backend vendor.

- Chromium: all 14 dashboard/workspace browser tests passed (44.7 seconds).
- JavaScript rendering: all 5 tests passed, including gauge clamping, unsafe
  references, description escaping and source-isolated request sharing.
- Adapter/panel regression checks: 6 focused tests passed; final follow-up
  validation passed after tightening response/error handling.
- Storage: all 4 migration tests passed, including replay when migration history
  is absent. Existing source rows retain Prometheus type during schema-8 upgrade.
- Real Loki 3.7.9: pushed two synthetic errors, retrieved both and grouped them
  into one recurring pattern. See [Loki result](loki-live.json).
- Real Tempo 3.1.1: OTLP ingestion, trace-by-ID retrieval and adapter search
  returned one 25 ms synthetic trace. Search was initially empty and succeeded
  after backend indexing; no indexing-latency SLA was measured. See
  [Tempo result](tempo-live.json).

VictoriaMetrics, Mimir and Thanos use the same Prometheus-compatible adapter;
this report does not certify a live installation of each vendor. CloudWatch,
Azure Monitor, Google Cloud Monitoring, OpenSearch, Elasticsearch, Splunk,
Datadog, InfluxDB and SQL adapters are not implemented in this change.

Only the disposable demo was upgraded. Its schema-7 volume remains preserved;
the schema-8 preview uses a separate copied volume. Restore the matching
pre-upgrade database/key for rollback; old binaries cannot open schema 8.

Protocol references: [Loki HTTP API](https://grafana.com/docs/loki/latest/reference/loki-http-api/),
[Tempo HTTP API](https://grafana.com/docs/tempo/latest/api_docs/),
[VictoriaMetrics URL examples](https://docs.victoriametrics.com/url-examples.html).
