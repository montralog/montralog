# Project structure

    montralog/
    ├── src/montralog/           Application package
    │   ├── config.py           Version, constants and environment configuration
    │   ├── http.py             WSGI transport, routes and response security
    │   ├── accounts.py         Local accounts, sessions, profiles and saved dashboards
    │   ├── security.py         Read/ingest authorization and startup validation
    │   ├── validation.py       Field validation, redaction and message grouping
    │   ├── ingestion.py        Transactional logs/spans/samples/events ingestion
    │   ├── otlp.py             OTLP JSON mapping
    │   ├── queries.py          Telemetry queries and correlation views
    │   ├── metrics.py          Allowlisted Prometheus queries and templates
    │   ├── storage.py          SQLite/PostgreSQL adapters and schema management
    │   ├── migrations/         Ordered SQLite and PostgreSQL SQL migrations
    │   ├── static/             Browser HTML, CSS and JavaScript
    │   ├── cli.py              Operator commands
    │   └── wsgi.py             Production server entry point
    ├── agents/host/            Independently deployed host collector
    ├── deploy/
    │   ├── docker/            Local backend configuration and alert rules
    │   └── helm/montralog/    Chart, values schema, templates, production example
    ├── scripts/               Setup, smoke checks, chart validation and migration
    ├── tests/                 Gateway, storage and optional PostgreSQL tests
    ├── docs/                  Architecture, operations, release gates and guides
    ├── .github/workflows/     Application, image and chart verification
    ├── pyproject.toml         Python package metadata and optional dependencies
    ├── Dockerfile             Non-root gateway image
    ├── compose.yaml           Local deployment, preserving existing volumes
    └── .env.example           Configuration names only; no real credentials

Runtime state does not belong in source control. Local data, backups, build output,
virtual environments and credentials are ignored. Helm packages are release
artifacts, not source directories. Static assets are packaged with the application
so the installed wheel and Docker image serve the same interface.

The root manage.py and wsgi.py are small compatibility launchers for existing
operators. New code belongs in the package; new collectors belong under agents;
new deployment resources belong under deploy. Avoid introducing a new root-level
script for each feature.

## Ownership boundaries

Transport owns HTTP/status handling. Validation owns admissible telemetry.
Ingestion owns transactional writes. Storage owns SQL dialects and migrations.
Queries own read models. The browser consumes documented APIs rather than
querying databases or Prometheus directly. Deployment files configure these
components and never contain real credentials.
