# 0.8.2 security remediation evidence

On 22 November 2026, Artifact Hub reported **327** findings for chart 0.8.1: 2 critical, 120 high, 181 medium, 17 low and 7 unknown. These covered all four images, not only the Montralog application.

Local Trivy 0.76.2 scans of the candidate image set show **18** findings: **0 critical, 4 high, 9 medium, 0 low and 5 unknown**. See [image identities, counts and scope](comparison.json).

| Image | Old count | Candidate count | Candidate critical / high |
|---|---:|---:|---:|
| Montralog | 11 | 0 | 0 / 0 |
| Prometheus | 63 | 8 | 0 / 2 |
| Alertmanager | 225 | 8 | 0 / 2 |
| OpenTelemetry Collector | 28 | 2 | 0 / 0 |

The candidate refreshes the Alpine runtime, upgrades its OpenSSL/zlib packages and pins newer official upstream backend images. This is about a **94.5% reduction in reported occurrences**, not a guarantee of security or an Artifact Hub grade prediction. Duplicate CVEs in separate binaries/images remain counted; no deduplication, image hiding or report suppression is used.

## Disclosed remaining high findings

Both stable Prometheus and Alertmanager images contain `CVE-2026-78661` in `golang.org/x/net v0.61.0`; upstream identifies 0.62.0 as fixed. Each image contains two reported occurrences. The owner explicitly authorized publishing the reduction with these remaining highs documented.

[The scoped acceptance](../../../deploy/security/accepted-upstream-findings.json) matches exact image digests, CVE, package/version and maximum occurrence count. CI rejects criticals and all other/new highs, and retains accepted findings in the original reports and summaries. Montralog's application image retains its existing zero-HIGH/CRITICAL gate. Replace the accepted upstream digests when fixed official releases are available; do not generalize this exception to other findings.

## Final release evidence

[0.8.2 release assets](https://github.com/montralog/montralog/releases/tag/v0.8.2) are published only after full CI and exact-image acceptance pass. The security archive contains the application scan and `stack/` reports with all findings and package inventories. It also includes dependency/static reports; separate assets provide SBOM, browser, local-AI and load/recovery results, digests and checksums.

The local application scan is a development build; final image identity and measurements come from those release assets. Artifact Hub independently indexes/scans chart 0.8.2 after publication. Old 0.8.1 scores remain attached to that historical version. Actual counts can change as advisories and scanner data change. No independent penetration-test certification is claimed.
