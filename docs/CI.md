# MirvDesk CI strategy

MirvDesk intentionally separates quick development checks from expensive cross-platform builds.

## Fast CI

`MirvDesk Fast CI` runs automatically for pushes to `main`/`master` and for pull requests. It validates the mandatory self-hosted server configuration, MirvDesk repository invariants, shell/YAML syntax, Cargo metadata/lockfile consistency and patch whitespace. It is designed to finish in minutes and cancels an older run when a newer commit is pushed to the same branch.

Fast CI does **not** build every supported platform. Cross-platform compilation is deliberately kept out of the edit/push feedback loop.

## Full CI

`MirvDesk Full CI` performs the complete cross-platform build matrix without publishing release assets. It is started manually from GitHub Actions. Maintainers can also push a temporary `ci/full/*` branch to trigger it from Git.

The nightly workflow runs the same full matrix automatically and does not publish a nightly release.

## Release CI

A version tag such as `v1.5.1` runs `MirvDesk Tag Build`. Release CI builds and publishes the supported Windows, Linux, macOS and Android artifacts, generates the SBOM, and checks Linux packages for the configured `MIRVDESK_SERVER_URL` bootstrap value before publication.

Legacy 32-bit Windows/Sciter is not a supported MirvDesk release target and is not part of the matrix. Linux ARM64 remains part of full/release builds; it is not spent on every development push.
