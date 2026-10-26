# Release status

The Docker isolation and security release line is **0.8.0**, schema **6**. Use [the published release](https://github.com/montralog/montralog/releases/tag/v0.8.0) and its checksums/image digest, [Docker installation](CONTAINERS.md), [security upgrade](SECURITY-0.8.0.md) and [public reports](reports/README.md).

Customer hosting uses separate Docker stacks; shared-gateway/database SaaS is disabled. Production acceptance remains environment-specific: [readiness matrix](PRODUCTION.md).

Earlier releases and their immutable reports remain available as historical evidence. Changed source requires a new version; published image tags/releases are not silently replaced with new application code.
