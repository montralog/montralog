# Data sources

Montralog includes server-side adapters for the sources below. These query existing backends; adding a connection does not install a backend, configure exporters or copy historical data. The adapter baseline shipped in 0.8.2. Version 0.9.0 adds source-specific setup guidance, HTTP regression coverage and safer backend error responses.

| Source | Supported queries and panels | Base URL guidance |
|---|---|---|
| Prometheus | Guided metric queries; line, bar, stat, table and gauge | Base URL without `/api/v1` |
| VictoriaMetrics | The same guided metrics through its Prometheus-compatible API | Single node: base URL, usually port 8428. Cluster: include `/select/<tenant>/prometheus` |
| Mimir | Guided metrics through its Prometheus-compatible query endpoint | Query base URL, commonly with `/prometheus` prefix |
| Thanos | Guided metrics through Thanos Query | Query endpoint, not a Store or Sidecar address |
| Loki | Sampled logs, timelines and recurring patterns | Query gateway base URL without `/loki/api/v1` |
| Tempo | Trace search summaries and timelines | Query frontend base URL without `/api/search` |
| Montralog storage | Local logs, patterns, trace summaries and deployment events | Built in; no saved connection required |

## Connect and build panels

1. Open **Connect data**, choose the backend and enter its name and base URL.
2. Select no authentication, Basic authentication or a bearer credential. Saved credentials require HTTPS.
3. Choose **Test connection**, then **Save & test**. Saving requires a successful response. Zero results can mean a healthy backend with no matching data.
4. Open a dashboard, add or edit a panel, select the matching signal and choose the saved **Data source**. Metric sources appear for metric panels, Loki for logs/patterns and Tempo for traces.
5. Select the visualization, time window and supported filters, preview results, apply the panel and save the dashboard.

Only metrics connections can be the workspace default. An explicit panel source remains pinned; deleting that connection reports a missing source rather than silently switching servers. Changing the default does not move collectors or their historical data. Local Montralog records remain available independently of external sources.

## Query scope and limitations

- Metric adapters use the guided metric catalog; arbitrary PromQL is not exposed. A backend must contain the metric names and labels used by the selected catalog panel. Connection success does not prove that host, Docker or Kubernetes collectors are installed. Scrape targets and alert-management APIs vary between compatible products; query compatibility does not establish support for every Prometheus administrative API.
- Loki reads up to 100 recent records. The current selector expects a nonempty `service_name` label; service filtering matches that label and environment filtering matches `environment`. Severity is read from `severity` or `level` and filtered within the returned sample. Pattern counts describe the sample, not the full dataset. Free-form LogQL and full-text historical aggregation are not implemented.
- Tempo reads up to 100 search summaries, with service and environment resource filters. This is not a full span waterfall or complete trace retrieval. Text and severity filters do not apply to trace search.
- Multi-tenant backends requiring `X-Scope-OrgID` need an operator-managed trusted gateway that injects the fixed tenant header. Arbitrary custom headers and direct tenant-header configuration are not implemented. Keep separate customer stacks and credentials; do not expose an unrestricted shared gateway.
- These sources do not imply integrations for Elasticsearch, arbitrary SQL databases or every vendor-specific API.

## Docker networking and credentials

Requests originate from the Montralog server. Container `localhost` is the gateway itself. Use reachable service names or `host.docker.internal` for a Windows-host service. Reverse-proxy path prefixes are preserved.

Private endpoints require an exact `hostname:port` entry in `MONTRALOG_ALLOWED_DESTINATIONS`, for example `loki:3100,tempo:3200,metrics.internal:9090`. Recreate gateway and relevant workers after changing their environment. The configured bundled Prometheus endpoint is already approved. Do not allow destinations you do not control.

Only administrators can test, save, edit or delete connections. Signed-in viewers can see safe metadata and query configured sources within their customer stack. Passwords and bearer credentials are encrypted with the deployment key and are not returned to the browser. A blank credential preserves an existing secret only for the same authentication type and endpoint; endpoint changes require re-entry.

TLS verification remains enabled. Credentials require HTTPS. DNS addresses are validated and pinned per request; redirects and environment proxies are not followed. Metadata/link-local destinations remain blocked even when allowlisted. Back up the database and matching encryption key together; see [Docker operations](CONTAINERS.md) and [recovery](ASSURANCE.md).

## Verification

`tests/test_source_http.py` exercises all six saved adapters against a disposable HTTP contract fixture: saving connections, path prefixes, query parameters, Loki/Tempo records, dashboard source references and malformed-response errors. It uses the real outbound transport without mocking adapter responses. This verifies the client contract, not a live deployment of each vendor or a vendor certification. Existing tests separately cover encryption, credential transport, DNS/redirect policy and signal validation. Validate your actual endpoint, authentication and metric schema before production adoption.

Official API references: [Prometheus](https://prometheus.io/docs/prometheus/latest/querying/api/), [VictoriaMetrics](https://docs.victoriametrics.com/url-examples/), [Loki](https://grafana.com/docs/loki/latest/reference/loki-http-api/), [Tempo](https://grafana.com/docs/tempo/latest/api_docs/).
