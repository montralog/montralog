# Storage, migrations and recovery

SQLite remains the default for local Docker upgrades to preserve existing named
volumes. PostgreSQL is an optional adapter for replicated gateways and the Helm
production profile. Storage choice must be explicit; changing a connection string
does not copy existing data.

## Schema lifecycle

Ordered SQL files live in src/montralog/migrations/{sqlite,postgresql}. The
schema_migrations table records applied versions. Initial migration adopts an
existing compatible 0.1 SQLite schema without deleting records. PostgreSQL
startup migration is serialized by an advisory lock. A database newer than the
application schema is rejected; rollback never silently downgrades it.

Connections have bounded waits. PostgreSQL connect timeout is five seconds,
statement timeout ten seconds, lock timeout five seconds. SQLite uses a five-second
busy timeout and a ten-second progress-handler deadline. Storage errors become
generic HTTP 503 responses rather than exposing connection strings.

PostgreSQL connections are opened per request/transaction; there is no global
cross-process pool. Bound Gunicorn worker/thread counts and use an operator-managed
pooler if needed. Benchmark before increasing replicas and database connection load.

Retention commits in batches of at most 5000 rows to avoid one giant transaction.
The PostgreSQL chart uses one non-overlapping CronJob. SQLite runs retention
beside the gateway against the same local PVC/volume.

## Move an existing local installation to PostgreSQL

1. Pause sources and the retention worker; take a consistent SQLite backup using
   the backup command. Preserve the original volume and credentials.
2. Create an empty PostgreSQL database with appropriate TLS/privileges and backups.
3. Install the server dependency or use the gateway image. Set
   MONTRALOG_DATABASE_URL privately in the process environment.
4. Run:

       python scripts/migrate_sqlite.py path/to/consistent-snapshot.db

   The script reads SQLite in read-only mode, requires empty target telemetry
   tables, imports in one transaction, preserves IDs and updates ID sequences.
   It refuses a nonempty target. Large imports may exceed the default timeout;
   plan/rehearse large migrations rather than improvising during an outage.
5. Verify per-table counts, times, representative queries and trace links.
6. Switch the deployment to PostgreSQL and resume sources. Confirm live ingestion
   and retention. Keep the old snapshot/volume for the agreed rollback window.

The original snapshot is never modified. The test suite uses only isolated test
databases; it must not be pointed at production.

## Backups

SQLite backup uses its native online backup API. PostgreSQL deployments need
native backups/PITR and a rehearsed restore owned by the database operator.
The application's backup command intentionally refuses to pretend SQLite backup
is a PostgreSQL backup. Prometheus/Alertmanager state and configuration need their
own backup policy.

Two gateway replicas improve process availability; they do not make an external
database, Collector, Prometheus, storage class or single cluster node highly
available. Publish recovery objectives only after failure and restore drills.
