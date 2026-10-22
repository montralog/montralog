# Artifact Hub publishing

Artifact Hub indexes the Helm repository hosted at:

https://montralog.github.io/montralog

The manually dispatched `Publish Helm repository` workflow publishes the existing
`v0.5.0-rc1` release chart, without repackaging or changing its version. It currently
publishes only that preview. Extend the repository to retain all released versions
before publishing a subsequent chart; do not replace an existing version's archive.

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
helm show chart montralog/montralog --version 0.5.0-rc.1
```

This is a public preview requiring your own application image and protected Secrets.
Follow [the chart installation guide](../deploy/helm/montralog/README.md) before installation.
