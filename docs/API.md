# API reference — 0.2.1-rc1

API reads require Authorization: Bearer <MONTRALOG_READ_TOKEN>.
Ingestion requires Authorization: Bearer <MONTRALOG_INGEST_TOKEN>.
Credentials must differ and each contain at least 32 characters. Read-token
holders can read all telemetry. No tenant isolation. Never put tokens in URLs.

## Read routes

| Endpoint | Response |
|---|---|
| GET /healthz | Public liveness/version; not dependency readiness |
| GET /livez | Public liveness alias for Kubernetes |
| GET /health/ready | Public database readiness, no telemetry payload |
| GET /readyz | Authenticated SQLite read check |
| GET /api/overview | Totals, observed services, log counts per minute |
| GET /api/logs | 100 newest logs, offset and has_more |
| GET /api/patterns | Up to 100 service/environment message groups |
| GET /api/traces | Up to 100 traces, or 1000 spans with trace_id |
| GET /api/samples | Up to 2000 newest host samples |
| GET /api/events | Up to 100 newest change events |
| GET /api/dashboards | Fixed template metadata |
| GET /api/metrics?panel=cpu | Allowlisted Prometheus range query |
| GET /api/targets | Prometheus scrape targets |
| GET /api/alerts | Prometheus pending/firing alerts |

Local queries accept minutes (1–10080, default 60), service and environment.
Logs also accept case-insensitive literal substring q, severity, trace_id, offset (0–100000).
Trace trace_id is nonzero 32-character hex. Metrics accept minutes up to 1440;
service/environment filters do not apply and the UI labels this.
Arbitrary PromQL or backend URLs are not accepted from users.

The overview caps services at 200. Other result caps can also truncate data.
Offset pages can shift during live ingestion. Error-log counts are not request
error rates. Trace duration is the envelope of spans observed within filters,
not necessarily full end-to-end latency.

## JSON ingestion

POST /api/logs, /api/spans, /api/samples or /api/events.
Content-Type must be application/json. Body is an array of 1–1000 objects, max
2 MiB. All records validate before the transaction. Time is Unix seconds, default
receipt time, nonnegative and at most five minutes into the future. HTTP 201
returns accepted count. Duplicate spans do not count as newly accepted records.

Common fields: service (required, max 200 characters), environment (default default,
max 200 characters), time (optional). Unknown fields outside attributes are ignored.

Log example:

    [{"service":"checkout","environment":"prod","severity":"ERROR",
      "message":"Database timeout after 150 ms",
      "trace_id":"abababababababababababababababab",
      "attributes":{"deployment.version":"v42"}}]

Severity: TRACE/DEBUG/INFO/WARN/ERROR/FATAL, default INFO. Message max 16384 chars.
Optional trace_id must be nonzero 32-character hex. Attributes max 64 top-level
keys and 16384 serialized characters. Redaction is best-effort, not a guarantee
against PII, secrets, connection strings, headers or query parameters.

Span example:

    [{"service":"checkout","environment":"prod",
      "trace_id":"abababababababababababababababab",
      "span_id":"cdcdcdcdcdcdcdcd","parent_id":"",
      "name":"POST /checkout","duration_ms":42.5,"status":"ERROR"}]

Trace IDs are 32 hex characters; span/parent IDs are 16; all IDs nonzero.
Parent can be empty. Status UNSET/OK/ERROR. Duration finite and nonnegative.
Attributes supported. Spans deduplicate by trace_id/span_id.

Sample example:

    [{"service":"host-a","environment":"prod",
      "name":"host_cpu_usage","value":12.5,"unit":"%"}]

Values must be finite. Names use Prometheus identifier syntax. These samples
power the host table; they do not enter the Prometheus store or its alert rules.

Event example:

    [{"service":"checkout","environment":"prod","kind":"deployment",
      "message":"Deployed version v42"}]

## OTLP adapter

POST /v1/logs and /v1/traces accept OTLP JSON envelopes with ingest auth.
Valid empty envelopes return HTTP 200 and an empty object. Binary protobuf, gzip
and gRPC are not implemented in this gateway. Send those to the bundled collector,
which converts log/trace export to uncompressed JSON. Metrics go to its Prometheus
exporter, not to /v1/metrics on the gateway.

Retained subset: service/environment/resource and record attributes, message body,
numeric severity, trace/span/parent IDs, name, timing and numeric status.
Span events/links/kind, scope metadata, dropped counts and flags are not retained.
Complex OTLP AnyValues may remain encoded objects in attributes. This is not full
OTLP storage fidelity.

Errors: 400 invalid fields; 401 wrong credentials/role; 404 unknown route;
413 missing/oversized body; 415 content type; 503 SQLite error.
Use exponential backoff/jitter for transient failures. Logs can duplicate.
Network deployments require front-proxy body/time/connection/rate limits.

Browser accounts, session endpoints and personal dashboards are described in [ACCOUNTS.md](ACCOUNTS.md). Browser sessions have telemetry read access; ingestion still requires the separate ingest bearer token.

## Browser endpoints

`GET /api/auth/status` reports whether local accounts exist. `POST /api/auth/login`
accepts a JSON object with username/password and returns a session cookie, safe
user fields and a CSRF token. No registration endpoint is exposed.

Authenticated browser endpoints:

- `GET /api/account`: current profile, session expiry and CSRF token.
- `POST /api/account/logout`: revoke current session.
- `POST /api/account/profile`: update name and optional email.
- `POST /api/account/password`: current_password and password; revoke all sessions.
- `GET /api/account/sessions`: current and other session creation/expiry times.
- `POST /api/account/revoke`: revoke all other sessions.
- `GET /api/saved-dashboards`: account-owned saved dashboards.
- `POST /api/saved-dashboards`: name plus definition containing panels and minutes.
- `POST /api/saved-dashboards/delete`: delete an account-owned dashboard by id.

All browser POSTs except login require `X-CSRF-Token`. Bodies must be JSON objects
no larger than 16 KiB. Bearer tokens cannot mutate browser account resources.

## Studio controls (0.3)

`POST /api/saved-dashboards` accepts an optional id to update an owned dashboard.
Definitions accept legacy metric ids or validated panel objects with source,
visual, metric, title, width and bounded filters. See STUDIO.md for supported types.

Administrator session/CSRF endpoints:

- `GET/POST /api/control/tokens`: list metadata; create named read/ingest tokens
  with days=1,7,30,90; revoke with action=revoke and id. Full token is returned
  once on creation.
- `GET/POST /api/control/channels`: masked metadata; save Slack contact points;
  action=test queues a message; action=delete cancels pending deliveries.
- `GET /api/control/deliveries`: safe delivery status and attempt history.
- `GET/POST /api/control/rules`: list/create/edit/pause/delete bounded metric or
  log-count rules. `GET /api/control/inbox` is available to signed-in viewers.

`POST /v1/metrics` now accepts a managed ingest bearer token at the gateway and
forwards the validated JSON request to the configured private collector. Direct
collector listeners retain deployment-level bearer credentials.


For company-login configuration and access boundaries, see [Identity](IDENTITY.md). The browser control APIs require a session and CSRF verification; machine read/ingest tokens do not administer organization access.
