# Dashboard creation verification — 1 November 2026

These are development checks and synthetic demos, not a production certification,
independent penetration test or release publication.

- 17 browser flows passed, covering Settings-only themes, Windows/Linux starters
  with 8/10 panels, direct saved-panel editing, multi-selection and AI draft review.
- An additional browser rerun verified AI panels append without changing the draft
  name or automatically saving it.
- 15 API/worker regressions, 6 renderer checks and 6 identity tests passed locally.
- 11 real PostgreSQL tests passed after correcting LIKE-pattern parameter handling;
  SQLite queue checks and scoped-worker tests passed as well. The PostgreSQL test
  database was an isolated disposable `montralog_test` instance, never operator data.
- Local Ollama `qwen3:4b` returned a validated four-panel draft. Saved dashboards
  were unchanged. Live build: `df2f41c`. See [result and limitations](ollama-panel-draft.json).
- Dependency audit reported zero known vulnerabilities for seven resolved packages
  under local platform markers. `joserfc` is pinned to 1.7.6 in both manifests.
  See [dependency report](dependencies.json). Linux/container checks run separately
  in the [PR verification workflow](https://github.com/montralog/montralog/pull/10/checks).

The live demo contains Windows systems (8 panels), Linux systems (10) and
Applications (12), with a 24-panel limit per dashboard. Names indicate example
organization, not validation of physical Windows/Linux machines. Missing sources
show empty states; the demo uses synthetic telemetry.

AI sends only the supplied description and the supported metric catalogue to the
approved provider. The response cannot contain arbitrary queries, URLs, source IDs
or executable settings. Role/provider policy is rechecked by the worker. Hosted
providers require operator and per-request sharing approval. A draft can be wrong:
the live log panel required a manual severity-filter check despite its title.
Review sources, thresholds and filters before saving.

Long investigations can use a separate worker pool from panel generation. Both
retain the same authorization, budget and no-automatic-remediation policies.
