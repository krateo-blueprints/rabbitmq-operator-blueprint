---
type: ExampleIndex
title: rabbitmq-operator-blueprint examples
description: The example Compositions and what they show.
resource: rabbitmq-operator
tags:
  - krateo
  - blueprint
  - rabbitmq
  - examples
timestamp: 2026-11-18T00:00:00+00:00
---
# Examples

- [examples/basic/cluster-operator.yaml](../examples/basic/cluster-operator.yaml): the cluster-operator, 2 replicas.
- [examples/basic/topology-operator.yaml](../examples/basic/topology-operator.yaml): the messaging-topology-operator,
  2 replicas.

Both name the version this release serves; `hack/release-preflight` refuses a tag they do not name.
