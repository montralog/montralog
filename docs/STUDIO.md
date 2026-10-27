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
