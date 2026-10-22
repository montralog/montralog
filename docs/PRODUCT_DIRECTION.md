# Product direction

Production engineering and product usefulness need separate evidence. A Helm chart
improves operations; it does not establish market preference. Prioritize one
workflow that operators can complete reliably before adding broad feature lists.

## Initial audience

Small engineering teams operating applications, Linux/Windows hosts, Docker and
Kubernetes. They already emit telemetry but spend too much time connecting signals.
Start with one organization per deployment, not an unqualified multi-tenant SaaS.

## Core experience

1. Connect a source and show whether telemetry is arriving, delayed or absent.
2. Discover its service and open a useful view without authoring a dashboard.
3. Search a failure, identify repeated messages, and inspect linked request spans.
4. Compare deployment/change events in the same environment/time window.
5. Export evidence or follow an operator-owned runbook.

Never label no-data as healthy, log counts as request error rates, correlation as
proven cause, or a chart template as a fully working integration.

## Pilot acceptance targets

Validate these with users; they are targets, not measured achievements:

- New operator gets representative real telemetry in under 10 minutes.
- Operator identifies a relevant failing service and trace without learning SQL.
- Filters and time windows stay consistent during an investigation.
- Failure messages explain which connection or permission to check.
- Installation, backup and upgrade can be repeated from documentation.
- UI remains usable at desktop/mobile widths and with keyboard navigation.

Record completion rate, time to useful data, investigation time, confusing states,
alert quality, ingestion loss and operator maintenance effort. Use those results
to choose the next release instead of claiming to be best in the market.

## Next product increments

Integration diagnostics, resource freshness, saved investigations, runbook links,
template detection, editable dashboards, SLO views, hierarchical span trees,
deployment comparison and scoped user access. Each needs functional tests plus
feedback from an actual operator; AI explanations remain optional and evidence-linked.
