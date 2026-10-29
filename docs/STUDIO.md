# Dashboards, timelines, alerts and access — 0.3

Browser access uses a username/password session. Fresh installations have no shared default password. Create an account using the operator CLI. Each account has personal dashboards; telemetry remains shared within its customer stack.

## Dashboard studio

Open Dashboards → Create dashboard. Choose a name and time window; add up to 24
panels, or save an empty canvas and add panels later. Saving includes current panel edits. Use **Preview panel** to check its data before applying it. A panel can use:

| Signal | Views |
|---|---|
| Prometheus metric | Line chart, bar chart, statistic, table |
| Logs | Table, timeline |
| Log patterns | Table, frequency bars |
| Changes / deployment events | Table, timeline |
| Traces | Table, timeline |

Panels have a title and half/full row width. Edit, duplicate, remove, resize or move panels up/down before
saving the dashboard. Apply or discard an unfinished panel before switching to another canvas action. Existing saved dashboards can be reopened and edited.
Service/environment filters apply to logs, patterns, changes and traces. Literal
message search and severity apply to log panels. Metric panels use a supported
Prometheus query; arbitrary PromQL and arbitrary layout coordinates are not exposed.
Multiple timeline panels can show different services or signals side by side.

Timeline navigation also combines recent logs, changes, traces and in-app alert
transitions. Queries are bounded: 100 log rows, patterns, traces or changes per
source. The combined timeline displays at most 120 entries. These are investigation
views, not an exhaustive audit export. Message grouping is deterministic; nearby
events and matching patterns do not establish causation.

## API tokens

Administrators can create read or ingest tokens with 1, 7, 30 or 90 day expiry.
The full secret appears once. Database storage contains only its SHA-256 hash,
prefix, scope, expiry, last-use timestamp and revocation status. Read tokens
cannot ingest; ingest tokens cannot read telemetry or administer browser accounts.
Revocation takes effect on subsequent requests. Tokens are installation-scoped,
not scoped to an individual service or tenant.

Use gateway port 8080 for JSON ingestion or OTLP HTTP `/v1/logs`, `/v1/traces` and
`/v1/metrics`. Metrics are forwarded to the configured private collector. Direct
collector ports 4317/4318 still use the separate deployment-level ingest token
from the operator's Secret/.env. Those bootstrap credentials are managed through
deployment configuration, not through the managed token table.

## Alert rules

Administrators create metric threshold or matching-log-count rules. Metric rules
use the highest series value for Above or lowest for Below. Log counts cover the
last five minutes with optional literal text, severity, service and environment.
Choose a hold duration and optional Slack contact points. The notification worker
evaluates enabled rules every 30 seconds. Missing metric data is UNKNOWN, not a
healthy/normal observation. Rules transition through NORMAL, PENDING and FIRING.
Firing and resolved transitions go to the in-app inbox. Repeated firing evaluations
do not generate repeated notifications while the state stays FIRING.

Workspace rules are separate from Prometheus's deployment-provisioned rules.
The latter remain visible in Alerts and use Alertmanager's separate delivery
configuration. This UI does not rewrite Prometheus configuration or automatically
route its alerts through the workspace contact points.

## Slack contact points

Under Notifications, add the incoming webhook for a Slack channel and enable it.
The UI never reads back the webhook. Edit with an empty webhook field to retain
the existing secret. Send test explicitly queues one test message; check delivery
history for SENT. A missing webhook is not a connected integration.

The endpoint is restricted to HTTPS `hooks.slack.com/services/...` and redirects
are rejected. Webhook secrets are stored in the protected installation database;
they are not encrypted separately at rest. Protect the database and its backups.
No log messages are sent to Slack automatically: rule messages contain the rule
name, state, observed value and condition description. Avoid sensitive rule names.

Deliveries persist and retry up to five attempts with backoff. The delivery model
is at-least-once: a crash after Slack accepts a message but before acknowledgement
is recorded can produce a duplicate. Run one notification worker per installation.
Compose runs one worker; Helm uses a SQLite sidecar or a single Recreate PostgreSQL
worker deployment. With Kubernetes network policies, permit outbound HTTPS to the
approved Slack/proxy destination using networkPolicy.extraEgress. No public
inbound webhook endpoint is opened.

References: [Slack incoming webhooks](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/),
[Prometheus query API](https://prometheus.io/docs/prometheus/latest/querying/api/).
## Canvas-first editing

The editable canvas shows actual panel contents with per-panel edit, duplicate, width, move and remove controls. **Add visualization** opens a separate side editor; applying the panel closes it and returns to the full canvas. Existing dashboards open in canvas mode rather than a list of panel forms.

In the side editor, select a signal and visualization using the view selector or visual choice buttons. Metric panels show metric/source choices; record panels show their relevant service/environment filters, and log views expose text/severity filters. Selection changes refresh the current panel preview without replacing the form or discarding typed input. Missing source data is shown explicitly instead of fabricated examples.

Use **Save dashboard** to persist the whole view. Closing an editor with unfinished changes requires applying or discarding that panel. No arbitrary PromQL or free-position layout coordinates are implemented.


## Guided metric queries and appearance

In **Dashboards → Create dashboard → Add visualization**, choose a data source,
metric, visualization, and aggregation. **Each series** preserves the original
metric; Average, Sum, Minimum, Maximum, and Series count aggregate it. Group by
Instance, Host, Container, Namespace, or Service when that label exists in your
exporter. Missing labels collapse into one unlabeled group; they do not create
resource metadata. Count reports series, not the metric's original unit.

Open **Generated Prometheus query** to inspect the expression before saving.
The server builds queries from supported metrics and validated operations.
This is a guided builder for the bundled metric catalog, rather than an arbitrary
PromQL editor. Log text and severity filters remain literal record filters.
Identical metric queries within one dashboard render share a request; subsequent
refreshes fetch fresh data.

Name and save multiple personal dashboards. Use **Find dashboard** in the library,
**Duplicate** to start an independent copy, and **Switch dashboard** in a saved
view to compare dashboards. Copies retain the data-source references; they do not
copy credentials or change access permissions. Existing owner checks still apply.

The header's **Theme** menu offers Dark, Light, Midnight, and System. The choice
is stored in this browser and synchronizes across its tabs. System follows the
operating-system preference. This is a device preference, not an account setting.


## Advanced panel controls

The editor supports one-third, half-row and full-row widths, plus compact,
standard and tall heights. Edit, duplicate, resize, reorder and remove controls
have accessible names and tooltips. Choose a panel icon, describe its meaning,
and attach an HTTPS documentation or runbook reference. References open in a
separate tab; Montralog does not fetch their contents.

Metric gauges accept finite minimum, maximum, warning and critical values with
`minimum < warning < critical <= maximum`. Values outside the range are labelled
with their actual value while the bar is clamped. Thresholds colour the display;
they do not create alert rules. Existing dashboards keep their prior layout.

## External backend adapters

| Backend | Panel support | Connection test |
| --- | --- | --- |
| Prometheus | Metric charts, bars, statistics, tables, gauges | Prometheus `up` query |
| VictoriaMetrics, Mimir, Thanos | Same, through their Prometheus-compatible query API | `up` query |
| Loki | Log tables, timelines and sampled patterns | Loki labels API |
| Tempo | Trace search summary tables and timelines | Tempo search API |

Choose a backend in **Connect data**, enter its query base URL, test and save.
Metric backends may become the workspace default. Log and trace panels select
their external source explicitly; a blank source uses Montralog storage.
Use the backend's query-frontend URL, including any required proxy path prefix.
A metrics API test does not prove exporter coverage or support for target/admin
APIs; those vary between compatible servers.

Loki's guided query uses `service_name` and `environment` labels. Without filters
it selects nonempty `service_name`; streams lacking that label are outside this
first adapter. Text uses a literal LogQL filter. Severity is filtered on returned
`severity` or `level` labels. Patterns summarize at most 100 returned records,
not the full result set. No remote logs are imported into local storage.

Tempo filters map to `resource.service.name` and
`resource.deployment.environment.name`. Trace summaries do not include a span
count or local trace details. The AI button is not offered for external log or
trace panels because those records are not yet captured by the AI evidence path.

Authentication supports none, basic, or bearer. Credentials require HTTPS and
are encrypted at rest. Existing SSRF, DNS pinning and redirect protections apply.
Private services need operator destination allowlisting. Custom tenant headers,
AWS SigV4, Azure/Google OAuth, SQL sources, OpenSearch, Elasticsearch, Splunk,
InfluxDB and Datadog are **not implemented adapters** in this change. Do not treat
them as supported simply because they expose HTTP endpoints.

### Upgrade and backup

This development change adds schema migration **8**, recording backend type on
saved connections. Existing sources migrate as Prometheus. Back up the database
and encryption key before upgrading. Older schema-7 binaries cannot open a
migrated database; rollback requires the pre-upgrade database backup and matching
key. Adapter tests use fixtures unless a report explicitly names a live backend.
