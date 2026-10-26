# 0.7.0 assurance evidence

[Independent-agent security review](security-review.md) covers the new isolation, backup, investigation and transport changes. It is not an external penetration-test certificate.

The release workflow publishes dependency/image/static scan JSON, SBOM, checksums, browser results and exact-image bootstrap/load/reliability-soak measurements as release assets. A workflow result, source revision and image digest must be inspected together. Do not reuse the 0.6 scan as evidence for 0.7.

Local checks: 15 provider/silo/assurance tests passed; 11 delivery/deadline tests passed; 11 investigation/account tests passed. Hosted providers were mocked with synthetic replies. Local Docker engine was unavailable; no local container throughput measurement is claimed. Hosted check results will supply Linux/container evidence before release.
