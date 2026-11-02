# Application screenshots

Screenshots are actual Montralog application captures, not generated mockups. All telemetry shown is synthetic. No customer telemetry, model keys or connection credentials are included.

| Asset | View | Status and capture |
|---|---|---|
| `dashboard-library.png` | Applications (12), Linux (10), Windows (8) cards | Dashboard preview, 1 November 2026 |
| `dashboard-canvas.png` | Editable application panels, synthetic request rate | Dashboard preview, 1 November 2026 |
| `panel-presets.png` | Multiple preset selection with 12 existing panels | Dashboard preview, 1 November 2026 |
| `ai-panel-draft.png` | Completed four-panel Ollama draft, awaiting review | Dashboard preview, 1 November 2026; live Qwen3:4b |
| `advanced-dashboard.png` | Prometheus/Loki/Tempo synthetic lab | Earlier connector preview; see its verification report |
| `agent-investigation.png`, `agent-evidence.png` | Bounded incident analysis and evidence | 0.8.0 agent demonstration; synthetic incident |
| `dashboards.jpg`, `timelines.jpg`, `connections.jpg` | Earlier workspace views | Historical captures retained for existing references |

The first three captures were refreshed from the local demo using build `df2f41c`. The AI capture is the actual completed draft documented in [verification evidence](../../reports/dashboard-creation/README.md). It was not automatically saved. Titles and filters require review; the proposed ERROR log title did not set a severity filter.

Windows/Linux card names demonstrate dashboard organization, not validation of physical machines or native windows_exporter support. Values are synthetic and missing records are shown as empty states. These screenshots do not establish production capacity or root-cause accuracy.

To refresh images, use a non-production stack with synthetic fixtures, capture the relevant UI without personal profile details or secrets, update this table, and verify every README image path before committing. Preserve historical captures when other versioned documents reference them.
