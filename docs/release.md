---
type: Runbook
title: Releasing the RabbitMQ operator blueprints
description: The one-version scheme for two upstreams, what a release refuses, and how to bump an upstream.
resource: rabbitmq-operator
tags:
  - krateo
  - blueprint
  - rabbitmq
  - release
timestamp: 2026-11-18T00:00:00+00:00
---
# Release

## One version for both charts

Both charts carry `version: CHART_VERSION`, stamped from the git tag, and so does each CompositionDefinition. Each
chart's `appVersion` is its upstream's version. A chart wrapping a single upstream may instead commit a literal version
equal to upstream's (krateo-blueprints/charts PUBLISHING.md, "charts that version independently"), which keeps an
upstream bump from moving its served apiVersion. Here one tag stamps both charts, and the two upstreams (cluster-operator
2.23.2, messaging-topology-operator 1.20.5) cannot both equal it. So this repository has its own version line, starting
at 0.1.0, and every release moves both served versions together: `composition.krateo.io/v<X-Y-Z>`.

## Releasing

1. `lint.yaml` must have succeeded on the commit (`release-tag.yaml` refuses otherwise).
2. Update `examples/basic` to `composition.krateo.io/v<X-Y-Z>` of the version you are about to tag.
3. Tag `X.Y.Z` on that commit.

`release-tag.yaml` then runs, in order:

- **preflight**: krateo-blueprints/charts `release-preflight.yaml` (1.1.0) runs `hack/release-preflight X.Y.Z`. It
  refuses a version that is not plain X.Y.Z, examples that name another version, a chart or CompositionDefinition
  without the `CHART_VERSION` placeholder, and a vendored manifest whose digest moved. A refusal publishes nothing.
- **package-and-push**: stamps the charts and CompositionDefinitions, packages each chart once with its
  CompositionDefinition inside, checks the archive, and pushes it to `oci://ghcr.io/krateo-blueprints/charts`.
- **publish-index**: the org publisher (`publish-chart.yaml`, 1.1.0) puts the same bytes on the **blueprints** channel.

## Pre-releases

A tag reaches the Marketplace. To install a commit through Compositions before tagging it (the #309 H2 live tests in
krateo-openstack-blueprint), dispatch `prerelease.yaml` with `ref` set to the commit, branch or tag:

```console
gh workflow run prerelease.yaml -R krateo-blueprints/rabbitmq-operator-blueprint -f ref=<commit>
```

It derives the version with `hack/release-version.sh derive`: the base is the version `examples/basic` serve (so the
pre-release precedes the release it will become; give `base` to override, it must be newer than every release tag),
then `-main.g<sha7>` for a commit on main, `-dev.g<sha7>` otherwise. It refuses a commit `lint.yaml` never passed on,
stamps `CHART_VERSION` in both charts and both CompositionDefinitions, pushes both charts to
`oci://ghcr.io/krateo-blueprints/charts` at that version, and uploads a run artifact `prerelease-<version>` with the
stamped CompositionDefinitions and the examples restamped to `composition.krateo.io/v<version, dots to dashes>`. The
run summary prints the `gh run download` and `kubectl apply` lines.

What it cannot do, checked on every pull request by `hack/validate-prerelease-channel.py`, with mutations:

- **Reach the Marketplace.** It calls no reusable workflow (only `release-tag.yaml` calls the org publisher), references
  no secret but `GITHUB_TOKEN`, and has no index, gh-pages, git push or release step.
- **Tag or release.** Its permissions are exactly `contents: read` and `packages: write`, with no job-level override.
- **Be installed by accident.** `X.Y.Z-main.g<sha7>` is a semver pre-release: helm never resolves it without an exact
  `--version` (or `--devel`), and core-provider serves it at its own apiVersion, never at the release's.
- **Be released.** `hack/release-preflight` checks the tag with `hack/release-version.sh check release`, which refuses
  the pre-release shape.

A pre-release is not required before a tag: whether the live test passed is krateo-openstack-blueprint's call before it
pins a release of these charts.

## Pushing to GHCR

Both `release-tag.yaml` and `prerelease.yaml` push through krateo-platformops/.github's `chart-push` action, pinned by
commit (krateo-blueprints/charts PUBLISHING.md rule 14), in locate mode: the action outputs the path of its `push.sh`,
and each workflow's loop runs it once per chart. Until 2026-11-18 this repository carried its own copy,
`hack/push-chart.sh`, which became that action's push.sh; one implementation replaced the copy. `helm push` PUTs the manifest by
digest, then tags it, and the tag step first reads the manifest back by digest. GHCR has 404'd that read about a second
after accepting the PUT (`failed to perform "Tag" on destination: sha256:<digest>: not found`, prerelease run
44279368853), leaving an untagged manifest. On that exact error the script polls until the registry serves that digest
(10 polls, 3 s apart), then pushes the same archive again: helm derives the manifest from the archive and its
modification time, so the second push has the same digest, and the script fails if it does not. Any other error fails at
once; a digest still not served after the polls fails, naming it. The action's `push_test.py` drives the script with
stand-in `helm` and `curl`, and mutates it. Here, `hack/validate-chart-push.py` refuses a bare `helm push` or
`oras push` in any workflow, and an unpinned use of the action.

## Bumping an upstream version

1. Download the new release's asset and replace `blueprints/<chart>/chart/files/upstream/<asset>` with it, unchanged.
2. In `hack/upstream.yaml`, set the new `tag` and `sha256` (and `requires` if the new release needs other CRDs).
3. Set the chart's `appVersion`, `image.tag` and the `krateo.io/upstream` annotation to match.
4. Run the gates. `hack/validate-render.py` fails if the new manifest changed shape in a way the render template does
   not handle (a renamed container, a new namespace reference outside `rabbitmq-system`).
