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
- `validate-release-wiring.py`: the release preflight runs first;
- `validate-yaml-block-style.py`: block-style YAML only.

`preflight-refs.yaml` resolves every image reference. Tag `X.Y.Z` after updating the examples to
`composition.krateo.io/v<X-Y-Z>`; the release runs `hack/release-preflight` first. See
[docs/release.md](docs/release.md).
