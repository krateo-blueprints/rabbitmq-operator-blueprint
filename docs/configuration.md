---
type: Configuration
title: rabbitmq-operator-blueprint configuration
description: The value surface each chart exposes, and what it changes in the upstream manifest.
resource: rabbitmq-operator
tags:
  - krateo
  - blueprint
  - rabbitmq
  - configuration
timestamp: 2026-11-18T00:00:00+00:00
---
# Configuration

Both charts expose the same closed set of values (`values.schema.json` refuses any other key):

| key | default | effect |
|---|---|---|
| `replicas` | `2` | operator Deployment replicas; leader election makes extra replicas standbys |
| `image.repository` | upstream's | the operator image |
| `image.tag` | upstream's (`2.23.2` / `1.20.5`) | kept equal to `appVersion` by `hack/validate-version-mirror.py` |
| `image.pullPolicy` | `""` | empty keeps upstream's (none set) |
| `podAntiAffinity.type` | `preferred` | `preferred`, `required` (needs as many schedulable nodes as replicas) or `none` |
| `podAntiAffinity.topologyKey` | `kubernetes.io/hostname` | the spread domain |
| `podDisruptionBudget.maxUnavailable` | `1` | the PDB, rendered with more than one replica |
| `resources` | `{}` | empty keeps upstream's requests and limits |
| `nodeSelector` | `{}` | operator pod placement |
| `tolerations` | `[]` | operator pod tolerations |
| `global` | `{}` | injected by the Krateo installer; unused |

Nothing provider-specific is defaulted. Everything not listed is upstream's, unchanged
([overview.md](overview.md)).
