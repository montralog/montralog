# Functional review — 23 October 2026

This review executes the code and tests. It does not rely solely on previous README claims or historical CI results. Application version remains **0.5.0-rc1**, schema **5**; the documentation repair uses chart **0.5.0-rc.2**.

## Defects reproduced and fixed

| Defect | Reproduction | Result after the fix |
|---|---|---|
| Invalid Prometheus JSON escaped request handling and crashed response serialization | Backend bodies containing numeric `NaN`, `Infinity`, `-Infinity` or overflow `1e400` | Reject nonfinite JSON numbers and return a safe unavailable response; valid Prometheus string `"NaN"` remains supported |
| Invalid alert numbers silently changed rule semantics | Boolean thresholds, boolean waiting periods, fractional periods including `-0.5` | Reject booleans and nonfinite numbers; require whole seconds; invalid requests leave no rules behind |
| A missing metric sample broke all bar widths | One `NaN` series alongside a healthy series | Omit nonfinite samples before scaling; show an empty state when no finite samples remain |
| kind CI image import failed before Kubernetes deployment | Containerd reported a missing digest while importing an OCI index with `--all-platforms` | Export and import each required image explicitly for `linux/amd64` using the existing loader |
| Artifact Hub package lacked its README | Inspect the original published chart archive | Publish a new documented chart, retain the original archive and verify README, license, metadata and SHA-256 from the public download |

The Python regression tests failed before the input-handling fixes (five failed assertions and four erroring subcases). The dashboard rendering tests also failed before the bar fix. All targeted checks passed afterward.

## Executed evidence

- **Local Python 3.14:** 128 discovered test executions, 72 passed and 56 PostgreSQL tests skipped, in 260.214 seconds. A later addition exposes five further PostgreSQL regressions in hosted CI. The first run using the laptop's default environment failed to import two modules because `joserfc` was absent; installing the declared dependencies in an isolated environment resolved this.
- **Hosted Python 3.11 and 3.13:** all 133 test executions passed on each interpreter, including isolated PostgreSQL. [Executed application and Docker checks](https://github.com/montralog/montralog/actions/runs/39946050743). That run's Helm job failed during image import; it is not an overall successful run.
- **Frontend component checks:** three Node tests execute the actual dashboard renderer with mocked API/DOM helpers. They check selected data-source propagation, latest-value stat rendering, mixed finite/missing bar samples and empty-state output. These are component checks, not browser end-to-end coverage.
- **Real loopback HTTP exercise:** 1,000 synthetic logs, 20 batches of 50 and four concurrent clients; 1.035 seconds observed locally with a single-threaded test server. Every accepted count and final query total is asserted. This short exercise is not a capacity guarantee.
- **SQLite recovery exercise:** create an account and saved timeline dashboard, ingest logs, back up to a second database, delete source records, switch to the backup and verify telemetry, dashboard definition, existing session and a fresh account login. Only temporary data is used.
- **Artifact Hub:** confirmed the public listing renders the new chart README, installation instructions, logo and links.
- **Published chart:** downloaded `0.5.0-rc.2`, verified its digest against the live index and checked its README, license, logo metadata and unchanged application version. Chart `0.5.0-rc.1` remains downloadable.

**Final verification passed:** [all four jobs succeeded](https://github.com/montralog/montralog/actions/runs/39946441145) on commit `58adae9`: Python 3.11, Python 3.13, containers and Helm. The application matrix includes all 133 Python test executions on each interpreter, three frontend component tests, the HTTP recovery exercise and package build. Kubernetes checks install the SQLite topology, verify collector delivery and retained telemetry after pod restart, upgrade to a two-replica PostgreSQL topology, verify shared data on both replicas and perform a rolling restart.

## Functional assertions added

`tests/test_functional_review.py` checks malformed backend handling through the HTTP application, valid Prometheus string samples, invalid alert input persistence, log-alert filters and pending/firing/resolved deduplication using actual stored log counts, and cross-user dashboard update rejection. The same cases run against isolated PostgreSQL through `tests/test_postgresql.py`.

`tests/test_studio_rendering.cjs` exercises dashboard rendering. `scripts/functional_review_smoke.py` uses a real loopback HTTP listener and temporary SQLite database. Neither reads the operator's `.env` nor modifies operator data.

## Reproduce

Create a virtual environment, then run from the repository root:

```sh
python -m pip install -e ".[server]" -r requirements-dev.txt
python -m unittest discover -s tests -v
node --test tests/test_studio_rendering.cjs
python scripts/functional_review_smoke.py
```

PostgreSQL coverage requires `MONTRALOG_TEST_DATABASE_URL` pointing to a disposable database named `montralog_test`. The PostgreSQL suite clears test records. Never supply production credentials. Hosted CI provisions its own disposable PostgreSQL service.

## Work still requiring deployment evidence

- Live Microsoft Entra, Google Workspace and Okta sign-in, provider errors and real tenant configuration; current provider exchanges remain mocked.
- Actual Slack destination receipt and outage behavior with the operator's webhook.
- Browser end-to-end journeys across navigation, forms, responsive layouts and accessibility.
- Sustained representative load, retention pressure, disk-full behavior and supported capacity limits.
- Full production incident recovery, PostgreSQL failover, external dependencies, target-cluster networking/TLS and restore rehearsal.

The executed checks support a controlled pilot. They do not establish production certification, tenant isolation, high availability or an independent security audit. See [the production checklist](PRODUCTION.md).
