# Browser accounts and dashboards

Montralog uses operator-managed local accounts for the web interface. Accounts
share read access to installation telemetry. Each account owns its profile and
personal saved dashboards. Administrator/viewer roles, teams, groups and company-login setup are documented in [Identity](IDENTITY.md). There is no tenant isolation, invitation flow or email-based password recovery.

## Create the first account

Start the stack, then run this interactive command. The password prompt does not
echo your input. Use a unique password of at least 8 characters.

```powershell
docker compose exec gateway python -m montralog create-user --username admin --name Administrator
```

Open http://localhost:8080 and sign in. Additional accounts use the same command
with different usernames. For Kubernetes, run the command in a gateway pod with
`kubectl exec -it <gateway-pod> -- python -m montralog create-user --username admin --name Administrator`.
The account persists in the configured SQLite or PostgreSQL database.

## Profile and security

My profile lets users update their display name and optional contact email,
change their password and revoke other browser sessions. Contact email does not
send notifications. Password changes revoke all sessions. An operator can recover
an account with:

```powershell
docker compose exec gateway python -m montralog reset-password --username admin
```

Passwords use PBKDF2-HMAC-SHA256 with 600,000 iterations and a random salt.
Browser sessions expire after 12 hours and are stored as SHA-256 token hashes in
the database. Session cookies are HttpOnly and SameSite=Strict. Session mutations
require a per-session CSRF token. Sign out revokes the server-side session; a
previously copied cookie cannot restore it. Sign-in attempts are throttled in the
shared database (10 per source address and username over 15 minutes). This is a
basic throttle; internet-facing installations also need proxy-level limits.

Use HTTPS for remote access and set `MONTRALOG_COOKIE_SECURE=true`. Compose reads
this optional setting from `.env`. Helm enables secure cookies with ingress;
terminate HTTPS at the ingress as described in KUBERNETES.md. Proxy operators must
ensure clients cannot spoof their trusted network boundary.

Existing read and ingest bearer tokens remain supported by the API. A browser
session cannot ingest telemetry, and bearer tokens cannot edit user accounts or
personal dashboards. Never share ingestion credentials through the browser.

## Dashboards

The dashboard library includes host, container, Kubernetes and application
templates. Create a personal dashboard by choosing a name, metric panels and a
default window; save, open and delete it through the library. Saved dashboards
are stored in the database and survive sign-out and gateway restarts. There is a
limit of 50 per account. Dashboards query the existing Prometheus panel allowlist;
they do not accept arbitrary queries. The current builder supports panel
selection and a 15-minute, 1-hour, 6-hour or 24-hour window, rather than arbitrary
layouts or query editing. Service filters do not scope Prometheus metrics.

Data sources shows actual scrape target states/errors and observed services.
Connect data documents the collector and exporter setup. Settings shows runtime
version and installation guidance; deployment configuration is managed in source.
Missing metrics show an explanation and never generated sample measurements.

See STUDIO.md for the administrator role, dashboard/panel editor, managed tokens and notifications introduced in 0.3.
