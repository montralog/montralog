# Dashboard query performance — development evidence

This development change improves log browsing and dashboard scheduling. It is not included in the published 0.8.2 security image. It does not establish parity with Grafana/Splunk or certify a distributed observability service.

## One crore retained synthetic log records

The benchmark generated **10,000,000** synthetic rows in a separate, disposable SQLite database using the application's existing schema/indexes. It ran on the local Windows/Python 3.14.6 machine. The database file was 1,857,511,424 bytes. Direct SQL fixture creation is not application ingestion throughput.

| Operation | Observed result |
|---|---|
| Previous first-page query plus full matching COUNT | Database deadline exceeded after 10,012 ms |
| New first page, 100 records + one lookahead row | Median 1.344 ms; maximum 1.910 ms over ten runs |
| Following 100 cursor pages | Median 2.813 ms; maximum 4.471 ms |
| Page uniqueness | 10,100 returned IDs verified unique |

[Raw measurements](ten-million-log-reads.json). Reads were sequential, local and cache-friendly after fixture creation; this is not a cold-cache, network, concurrent-user or arbitrary-filter benchmark. Results depend on hardware, data distribution and indexes. Grouped overview/pattern queries, text scans, ingestion, retention, failover and sustained concurrent load are not certified by these numbers. High-volume telemetry should use purpose-built metric/log backends and workload-specific validation.

## Query changes

Log browsing reads at most 101 result rows per page and uses the extra row for `has_more`, eliminating the unconditional full matching count. The API also accepts an opaque cursor bound to the search filters and a one-hour snapshot lifetime. `(time,id)` ordering handles identical timestamps. The cursor also carries the maximum record ID captured on the first page, excluding new arrivals even when their timestamps are backdated. Retention/deletion can still remove records between pages; this is not a long-lived database transaction. Legacy offset requests still work, with their existing 100,000 offset cap. Deep offset and unindexed text filters can remain expensive; use cursors and selective filters.

Dashboards show a canvas immediately, then load panels independently with four concurrent requests. Identical queries share one request during a render. Navigation cancels browser telemetry requests (server-side bounded queries may still finish); obsolete queued panel queries are discarded. Requests have a 15-second browser deadline. Automatic refresh waits for the dashboard's pending queries so slow panels are not starved by refreshes.

## Tests and reproduction

- Five SQLite and five real isolated PostgreSQL pagination tests cover tied timestamps, new arrivals, changed/invalid cursors, exact pages and legacy offset behavior.
- Eight renderer/query tests cover rendering, request sharing, concurrency and obsolete queued work.
- Seventeen existing browser flows passed; two additional browser flows cover delayed-backend progressive loading and cursor Next/Previous navigation.

```sh
python scripts/benchmark_log_queries.py --database work/benchmark-new.db --records 10000000 --output work/benchmark-result.json
```

The benchmark refuses existing files unless `--existing-synthetic` is explicitly supplied; that mode checks the synthetic deployment identity, fixture text and expected maximum ID before measuring. It never deletes or prunes an operator database. Allow several minutes and a few GB of disk for fixture creation. Do not pass production paths. No standalone SQL server is required by the default Montralog Docker installation.
