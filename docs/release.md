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

There is no pre-release channel here: no workflow publishes `X.Y.Z-main.g<sha>` builds of these charts. Live
validation happens where they are consumed (krateo-openstack-blueprint #309), before a release is pinned there.

## Bumping an upstream version

1. Download the new release's asset and replace `blueprints/<chart>/chart/files/upstream/<asset>` with it, unchanged.
2. In `hack/upstream.yaml`, set the new `tag` and `sha256` (and `requires` if the new release needs other CRDs).
3. Set the chart's `appVersion`, `image.tag` and the `krateo.io/upstream` annotation to match.
4. Run the gates. `hack/validate-render.py` fails if the new manifest changed shape in a way the render template does
   not handle (a renamed container, a new namespace reference outside `rabbitmq-system`).
