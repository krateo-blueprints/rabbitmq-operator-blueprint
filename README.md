# rabbitmq-operator-blueprint

## What is this

Krateo blueprints for the [RabbitMQ cluster-operator](https://github.com/rabbitmq/cluster-operator) **v2.23.2** and
[messaging-topology-operator](https://github.com/rabbitmq/messaging-topology-operator) **v1.20.5**, as two
Compositions. Each vendors its operator's upstream release manifest unchanged and renders it with a short, gated list
of changes. Published to `oci://ghcr.io/krateo-blueprints/charts/rabbitmq-cluster-operator` and
`oci://ghcr.io/krateo-blueprints/charts/rabbitmq-topology-operator` on the **blueprints** channel.
krateo-openstack-blueprint uses them for a highly available RabbitMQ (#309).

## Install

cert-manager is a precondition, from any source (with Krateo, the installer's `features.ingress`). Both charts refuse
to render without its CRDs, with the reason on the Composition's status. Then register both CompositionDefinitions and
apply [examples/basic](examples/basic). See [docs/usage.md](docs/usage.md).

## Configure

`replicas` (default 2, leader-elected), `image`, `podAntiAffinity`, `podDisruptionBudget`, `resources`,
`nodeSelector`, `tolerations`. See [docs/configuration.md](docs/configuration.md).

## What these charts change about upstream

- No Namespace object; `rabbitmq-system` becomes the release's namespace.
- `helm.sh/resource-policy: keep` on every CRD, so removing a release never deletes the CRDs and the custom resources
  they hold.
- The operator Deployment takes replicas, image, anti-affinity, resources and placement from values, with a
  PodDisruptionBudget when it runs more than one replica.

Everything else is upstream's, byte for byte. See [docs/overview.md](docs/overview.md).

## Versioning

**One tag stamps both charts.** Each chart's `version` (and its CompositionDefinition's) is the `CHART_VERSION`
placeholder, replaced by the git tag at release. The repository has its own version line, starting at 0.1.0, and each
chart's `appVersion` is its upstream's version (2.23.2 and 1.20.5).

**Why not mirror upstream.** A chart wrapping one upstream may commit a literal version equal to upstream's, so an
upstream bump keeps its served apiVersion. Here one tag would have to equal two different upstream versions.

**The consequence.** Every release moves both served apiVersions together (`composition.krateo.io/v<X-Y-Z>`), an
upstream bump included, so consumers bump their Compositions' apiVersion with each release they adopt.
[docs/release.md](docs/release.md).

## Namespace

The convention for cluster-prerequisite blueprints is `<name>-system`, as krateo-openstack-blueprint uses
`openstack-system`. The CompositionDefinitions and the example Compositions live in `rabbitmq-operator-system`. The
release namespace replaces upstream's `rabbitmq-system`, so any namespace works.

## High availability

2 replicas with preferred hostname anti-affinity, and a PDB. Both operators are reconcilers that elect a leader, and
neither is on RabbitMQ's data path: if the leader's pod or node goes away, RabbitMQ keeps serving, and the standby
takes over reconciliation within a lease. One standby is enough, and preferred spreading still schedules on small
clusters. mariadb-operator is different: with semi-synchronous replication it performs the primary failover itself,
so its availability is the database's, which is why that blueprint is designed with 3 replicas and required
anti-affinity.

## Examples

[examples/basic](examples/basic): both Compositions. See [docs/examples.md](docs/examples.md).

## Docs

- [docs/overview.md](docs/overview.md): how the vendored manifest becomes a chart
- [docs/usage.md](docs/usage.md): preconditions, install order, upgrade
- [docs/configuration.md](docs/configuration.md): the value surface
- [docs/api.md](docs/api.md): the generated kinds and served versions
- [docs/release.md](docs/release.md): the version scheme and the release flow
- [docs/log.md](docs/log.md): what changed and why

## Develop & release

`lint.yaml` runs the gates in `hack/`:
- `validate-vendored.py`: the vendored manifests match upstream, byte for byte;
- `validate-version-mirror.py`: every version agrees;
- `validate-render.py`: the render, the HA defaults and the refusals;
- `validate-release-wiring.py`: the release preflight runs first, and every `uses:` is pinned by SHA;
- `validate-prerelease-channel.py`: `prerelease.yaml` publishes only a pre-release, to GHCR, never to the index;
- `validate-chart-push.py`: both workflows push through krateo-platformops/.github's `chart-push`, pinned by commit, and no workflow pushes bare;
- `validate-yaml-block-style.py`: block-style YAML only.

`preflight-refs.yaml` resolves every image reference. Tag `X.Y.Z` after updating the examples to
`composition.krateo.io/v<X-Y-Z>`; the release runs `hack/release-preflight` first. To install a commit before tagging
it, dispatch `prerelease.yaml` (`X.Y.Z-main.g<sha7>`, GHCR and a run artifact only). See
[docs/release.md](docs/release.md).
