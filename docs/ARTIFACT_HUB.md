# Artifact Hub publishing

Artifact Hub indexes the Helm repository hosted at:

https://montralog.github.io/montralog

The manually dispatched `Publish Helm repository` workflow downloads a chart from
an existing GitHub release selected through `release_tag`. It retains every prior
chart archive from the live index and verifies each previous digest before adding
the new version. It refuses to overwrite a chart version with different bytes.

Current release: `v0.5.1`, chart `0.5.1`, application `0.5.1`.
The original `0.5.0-rc.1` and `0.5.0-rc.2` charts remain available.

The repository is registered under the Montralog account. Its assigned ID is
`1c2a9013-1178-494e-af42-0291fc28f401`. Ownership metadata lives in
`deploy/helm/artifacthub-repo.yml` and is copied beside the published index.

## Register the repository

1. Create an account at https://artifacthub.io and sign in.
2. In the control panel, add a repository with kind **Helm**, name **montralog**,
   and URL **https://montralog.github.io/montralog**.
3. After registering, copy the repository ID from the control panel.
4. Add `artifacthub-repo.yml` to the published directory alongside `index.yaml`,
   containing `repositoryID: <the actual assigned ID>`, then republish.
5. Wait for Artifact Hub to process it and check any tracking errors.

The account registration and ownership verification are separate from chart hosting.
Do not claim a verified publisher badge until Artifact Hub grants it.

## Helm clients

```sh
helm repo add montralog https://montralog.github.io/montralog
helm repo update
helm show chart montralog/montralog --version 0.5.1
```

This is a public preview requiring your own application image and protected Secrets.
Follow [the chart installation guide](../deploy/helm/montralog/README.md) before installation.
