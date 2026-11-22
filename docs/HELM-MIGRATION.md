# Retired RC chart and supported image locations

Chart **0.5.1-rc.1** contains `image.repository: montralog` and `image.tag: 0.5.1-rc1`. This resolves to an unqualified Docker Hub image, and the matching RC image was not published on GHCR either. The chart archive can download while Kubernetes fails with `ImagePullBackOff` or `ErrImagePull`.

The archive remains unchanged for historical integrity. Its repository index entry is deprecated, and Artifact Hub metadata excludes this version from discovery. Artifact Hub applies repository metadata on its next processing cycle; an already-open old version link may remain visible until then.

## New installations

Use the published chart **0.8.1**, whose default application image is **ghcr.io/montralog/montralog:0.8.1**. Artifact Hub is a catalogue; chart archives are hosted on GitHub Pages and images on GitHub Container Registry. Public images require no registry account.

```sh
helm repo add montralog https://montralog.github.io/montralog/
helm repo update
helm show values montralog/montralog --version 0.8.1
docker pull ghcr.io/montralog/montralog:0.8.1
```

Provision the required customer-bound authentication and encryption Secrets, then follow the [chart installation guide](../deploy/helm/montralog/README.md). Docker Compose remains the recommended installation path for new deployments.

## Existing RC installations

Do not point the old chart at a newer application image as a shortcut. Upgrade the chart and application services together using the [0.8.1 release notes](RELEASE-0.8.1.md), [backup and recovery guide](ASSURANCE.md) and your cluster-specific storage procedure. Preserve customer identity, credentials, the original encryption key and all persistent data. Older pre-encryption installations need the documented credential migration before encrypted startup is enabled.

Version 0.8.1 uses schema 8. Rollback requires the pre-upgrade database backup and its matching key. Do not delete Secrets or PVCs to resolve image-pull failures. Test the migration on a restored copy before changing a live installation.

## Diagnose a pull failure

```sh
kubectl -n observability describe pod YOUR_POD_NAME
helm -n observability get values montralog --all
```

Inspect the actual image in pod events. `montralog:0.5.1-rc1` is the retired reference. For a supported version, check outbound access to `ghcr.io`, the exact image tag and the node architecture (published images support Linux/amd64). Sanitize Helm output before sharing it because operators may have put private values in overrides.

Chart publication now checks anonymous access to the exact default image and validates any configured digest before indexing a new chart. Existing historical archives are retained byte-for-byte.
