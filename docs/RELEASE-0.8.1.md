# Montralog 0.8.1

Build dashboards on a visible canvas, choose visualizations with live data previews and save changes reliably.

- Keep charts visible while editing; use per-panel edit, duplicate, width, order and remove controls.
- Open a separate side editor for source, metric and visualization choices. Show only relevant fields and refresh the preview without replacing typed input.
- Save empty dashboards, include unfinished panel edits when saving, retain drafts on failed requests and clear account-specific drafts at sign-out.
- Keep Apache-2.0 unchanged. Bundle the original license, project notice, separate branding guidance and third-party information under About & license. No proprietary use gate or license server is introduced.
- Add regression coverage for selection/preview behavior, empty creation, save/reload persistence, layout controls, retry and draft isolation.

Docker Compose is the supported installation path. Upgrade all Montralog application services together, including the optional investigation worker, to `ghcr.io/montralog/montralog:0.8.1`; pin the published digest for reproducible deployment. Back up first and preserve the existing `.env`, tenant identity, tokens, encryption key and volumes. Database schema remains **7**. No key rotation or reinitialization is required for an existing 0.8.0 stack. Older installations must follow the isolation/secret upgrade procedure in docs/ASSURANCE.md.

Release assets attach exact-image security reports, dependency inventory/SBOM, browser results, bootstrap/load/recovery measurements, local-model evaluation, checksums and image identity. Build provenance accompanies the published image. Short synthetic tests and automated scans do not constitute sustained sizing, causal AI accuracy or external security certification. Existing customer-silo and read-only AI boundaries remain unchanged.
