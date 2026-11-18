---
type: Component
title: rabbitmq-operator-blueprint
description: Krateo blueprints for the RabbitMQ cluster-operator and messaging-topology-operator, vendored from their upstream release manifests and published on the blueprints channel.
resource: rabbitmq-operator
tags:
  - krateo
  - blueprint
  - rabbitmq
  - operator
timestamp: 2026-11-18T00:00:00+00:00
---
# rabbitmq-operator-blueprint

Two Krateo blueprints, one per upstream operator, each vendoring that operator's release manifest unchanged:

| chart | upstream | generated kind | served at |
|---|---|---|---|
| `rabbitmq-cluster-operator` | [rabbitmq/cluster-operator](https://github.com/rabbitmq/cluster-operator) v2.23.2 | `RabbitmqClusterOperator` | `composition.krateo.io/v<release>` |
| `rabbitmq-topology-operator` | [rabbitmq/messaging-topology-operator](https://github.com/rabbitmq/messaging-topology-operator) v1.20.5 | `RabbitmqTopologyOperator` | `composition.krateo.io/v<release>` |

Published as `oci://ghcr.io/krateo-blueprints/charts/<chart>` on the **blueprints** channel, each with its
CompositionDefinition inside the archive. krateo-openstack-blueprint uses them for a highly available RabbitMQ (#309).

## Where to go next

- [overview.md](overview.md): how a vendored manifest becomes a chart, and the changes it gets
- [usage.md](usage.md): preconditions (cert-manager), install order, upgrade
- [configuration.md](configuration.md): the value surface
- [api.md](api.md): the generated kinds and versions
- [examples.md](examples.md): the example Compositions
- [release.md](release.md): the version scheme and the release flow
- [log.md](log.md): what changed and why
