---
type: API
title: rabbitmq-operator-blueprint API
description: The kinds core-provider generates from the two charts, and how their served version follows the release.
resource: rabbitmq-operator
tags:
  - krateo
  - blueprint
  - rabbitmq
  - api
timestamp: 2026-11-18T00:00:00+00:00
---
# API

core-provider generates one CRD per chart from its `values.schema.json`:

| chart | kind | group | served version |
|---|---|---|---|
| `rabbitmq-cluster-operator` | `RabbitmqClusterOperator` | `composition.krateo.io` | `v<X-Y-Z>` of the release |
| `rabbitmq-topology-operator` | `RabbitmqTopologyOperator` | `composition.krateo.io` | `v<X-Y-Z>` of the release |

Both are namespaced. The served version comes from the chart version, which is this repository's release version
([release.md](release.md)): release 0.1.0 serves `composition.krateo.io/v0-1-0`.

`spec` is the values surface in [configuration.md](configuration.md), validated at admission by the generated CRD.
The operators themselves serve their own APIs (`rabbitmq.com`: RabbitmqCluster, User, Vhost, Permission, Policy,
Queue, Exchange, Binding, Shovel, Federation and more), unchanged from upstream.
