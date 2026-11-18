---
type: Example
title: Both RabbitMQ operator Compositions
description: The cluster-operator and messaging-topology-operator Compositions, in the rabbitmq-operator-system namespace, at the version this release serves.
resource: rabbitmq-operator
tags:
  - krateo
  - example
  - rabbitmq
timestamp: 2026-11-18T00:00:00+00:00
---
# examples/basic

The two Compositions, as you apply them once both CompositionDefinitions are registered (docs/usage.md):

- [cluster-operator.yaml](cluster-operator.yaml): kind `RabbitmqClusterOperator`, the cluster-operator.
- [topology-operator.yaml](topology-operator.yaml): kind `RabbitmqTopologyOperator`, the messaging-topology-operator.

Both are served at `composition.krateo.io/v0-1-0`, the version of this repository's release that installs them,
and both live in `rabbitmq-operator-system` (docs/usage.md, the namespace convention).
Applying both at once converges: the topology operator refuses to render until RabbitmqCluster's CRD is served, and
then renders on the next reconcile.
