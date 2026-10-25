# Public container installation

Package: **ghcr.io/montralog/montralog**. Supported release image platform: **Linux/amd64**.

```sh
docker pull ghcr.io/montralog/montralog:0.5.1
```

Anonymous public pulls require no GitHub token. The package is linked to the repository's Packages section. Version `0.5.1` identifies the release; `latest` is a moving convenience alias. Use the digest published in `IMAGE_DIGESTS.txt` for repeatable deployments. The image includes OCI source/version/revision labels and GitHub build provenance.

## Docker Compose

Check out tag `v0.5.1`. Prerequisites: Docker Engine/Desktop with Linux containers, Compose v2 and host Python 3.11+ for the private bootstrap helper.

```sh
python scripts/setup.py
docker compose pull
docker compose up -d --wait --wait-timeout 180
docker compose exec gateway python -m montralog create-user --username admin --name Administrator
python scripts/check_install.py
```

Setup creates distinct machine credentials and an encryption key in a private `.env`; it never overwrites an existing file. Choose an individual administrator password at the prompt. No shared default browser account is installed. Open http://localhost:8080. Ports bind to loopback by default. Put HTTPS, secure cookies and access controls in place before remote access. Production roles, storage and notification destinations require operator configuration.

For an existing deployment, follow [the security upgrade procedure](SECURITY-0.5.1.md). Stable images require an encryption key. Preserve an existing key, and explicitly migrate any legacy plaintext integration credentials after backup. Do not substitute a new key for one that already protects credentials.

## Kubernetes

```sh
helm repo add montralog https://montralog.github.io/montralog
helm repo update
```

Follow the chart README to create the authentication and encryption Secrets first. The chart defaults to the public versioned image. For production, copy the production values example, configure external PostgreSQL and TLS, and set `image.digest` to the release digest. The image repository remains `ghcr.io/montralog/montralog`.

## Verify and operate

Release assets include checksums, image digest and scan reports. The workflow publishes source provenance for the image. Keep your deployment inventory pinned to the exact tested version/digest; record OS/architecture, storage and configuration. Validate backup restoration in staging before upgrades. Named volumes retain data when stopping Compose; `docker compose down -v` removes it.

The image runs as UID/GID 10001 with no installed runtime package managers. Rebuild from source to customize dependencies. Runtime storage belongs under `/data`; `/tmp` needs writable temporary space for readonly-container operation. The Compose and Helm profiles configure non-root execution, dropped capabilities and writable temporary storage. See the organization rollout and operations guides.
