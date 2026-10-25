# Guided data connections — 0.4

Connect data is now a source catalog and working server-side connection manager.
Browser login uses your account session; configuring a local Prometheus server
does not require a Montralog API token.

## Connect Prometheus

1. Open **Connect data → Prometheus → Add connection**.
2. Enter a connection name and Prometheus server URL. For this Docker stack,
   **Use local Docker Prometheus** fills `http://prometheus:9090`.
3. Choose **No authentication** unless the Prometheus backend requires Basic
   authentication or a bearer credential.
4. Use **Test connection**, then **Save & test**. Saving requires a successful
   Prometheus API response. The test reports the number of returned `up` series;
   zero series can still be a valid connection with no configured exporters.
5. Optionally select **Use as workspace default**. Infrastructure views, older
   dashboard panels and metric alert rules use that default.

Requests originate from the Montralog server, not from the browser. Inside Docker,
`localhost` refers to the gateway container. Use `host.docker.internal` for a
Prometheus server running directly on the Windows host, or a reachable Docker
service/network name. HTTPS uses normal certificate verification; there is no
skip-verification switch. A reverse-proxy path prefix is supported.

## Manage and use connections

**Data sources** lists saved sources, their authentication mode, default status,
last test result and current scrape targets from the default backend. Administrators
can test, edit and delete saved connections. Other signed-in users can see source
metadata and select a source in their personal dashboard panels.

In **Dashboards → Edit dashboard → Edit/Add panel**, select a **Data source** for a
metric panel. Workspace default follows future default changes; an explicit source
remains pinned to that source. If an explicitly selected source is deleted, its
panels report the missing source instead of silently querying another server.

The bundled deployment source is always available as a fallback and cannot be
deleted in the UI. Customize creates a saved connection rather than rewriting
environment or Helm settings. Existing logs/traces remain in Montralog's built-in
storage. The local Docker/host collector continues feeding the bundled Prometheus
instance; changing the workspace default does not move its data.

## Credentials and network access

Basic passwords and bearer credentials are submitted only through authenticated,
CSRF-protected administrator routes. The API never returns the secret. Editing
with a blank credential preserves the existing secret when authentication mode is
unchanged. Choosing No authentication clears stored credentials for that source.
Credentials are encrypted using the deployment's operator-held key. Saved Basic/bearer credentials require HTTPS; certificate verification cannot be disabled. Migrate old plaintext records using the [Docker upgrade guide](CONTAINERS.md).

Private destinations require an operator entry in `MONTRALOG_ALLOWED_DESTINATIONS`, for example `metrics.internal:9090,host.docker.internal:9090`. Set this in the private environment file and recreate the gateway and notification worker. Match the exact hostname and port; wildcards are not supported. Approve only DNS names and services you control. The operator-configured bundled Prometheus endpoint is already approved.

All resolved addresses are validated on each request. Connections use those numeric addresses directly, preserving TLS hostname verification; redirects and environment proxies are not followed. Link-local/metadata, multicast and unspecified destinations are always denied, even if allowlisted. Private DNS addresses may change between requests for approved internal services; use Docker networking and egress controls to restrict those services further.

Only the operator-configured collector may use HTTP with credentials, through the explicit `MONTRALOG_ALLOW_INSECURE_COLLECTOR=true` setting in the isolated Docker network. It is not a general exception for saved data sources. Do not expose that network or reuse its credentials across customers.

## Supported sources

Prometheus-compatible APIs support saved URL/authentication connections in this
release. Logs and traces are built-in Montralog stores. Docker/host metrics use the
existing local collector. External Loki, Tempo, Elasticsearch and SQL query-source
plugins are not implemented; they are not shown as working connectors.

The interaction follows Grafana's documented URL/authentication and Save & test
pattern: [Grafana Prometheus configuration](https://grafana.com/docs/grafana/latest/datasources/prometheus/configure/).
