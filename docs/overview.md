---
type: Architecture
title: rabbitmq-operator-blueprint architecture
description: How each upstream release manifest is vendored unchanged and rendered with a short, gated list of changes, and why there is no upstream Helm chart underneath.
resource: rabbitmq-operator
tags:
  - krateo
  - blueprint
  - rabbitmq
  - architecture
timestamp: 2026-11-18T00:00:00+00:00
---
# Architecture

## No upstream Helm chart, so the release manifest is vendored

Neither operator publishes an official Helm chart: each release ships Kubernetes manifests as release assets
(`cluster-operator.yml`; `messaging-topology-operator-with-certmanager.yaml`, whose bytes at v1.20.5 are identical to
`messaging-topology-operator.yaml`). Each chart carries its asset, byte for byte, in `chart/files/upstream/`, with its
SHA-256 recorded in `hack/upstream.yaml`. `hack/validate-vendored.py` checks the digest, and in CI that the file is
what GitHub serves for the tag today.

## The changes, applied at render time

`templates/manifests.yaml` reads the vendored file, splits it into documents and renders each with exactly these
changes:

1. **No Namespace object.** The release's namespace exists already; Helm should not own a Namespace.
2. **The release's namespace instead of `rabbitmq-system`.** Object namespaces, the Service DNS names in the
   cert-manager Certificates, cert-manager's `inject-ca-from` annotations, the webhook Service references and the
   RBAC subjects. The operators find their own namespace at run time (the service-account namespace file), so they
   work in any namespace.
3. **`helm.sh/resource-policy: keep` on every CustomResourceDefinition.** Upstream sets none. Without it, removing
   the release would delete the CRDs, and with them every RabbitmqCluster, User and Vhost in the cluster.
4. **The operator Deployment from values:** replicas, image, pull policy, pod anti-affinity, resources, nodeSelector,
   tolerations.
5. **A PodDisruptionBudget** (maxUnavailable 1) selecting the Deployment's pods, with more than one replica.

`hack/validate-render.py` derives the expected output from the upstream file independently, with the same five
changes, and compares object by object. Any other difference fails.

## High availability

Both operators elect a leader: the cluster-operator always (`LeaderElection: true` in `cmd/main.go` at v2.23.2), the
topology operator with the `--leader-elect` argument its manifest passes. Extra replicas are standbys. The default is
2 replicas, preferred anti-affinity by hostname, and the PDB. The operators are not on RabbitMQ's data path: a
standby only has to take over reconciliation.

## Preconditions refused, not documented

At these versions **both** operators serve their admission webhooks with certificates cert-manager issues (a
self-signed Issuer and Certificates in the manifest, and cert-manager injects the CA). The topology operator also
manages objects inside RabbitmqClusters. On a live cluster each chart refuses to render, naming what is missing, while
cert-manager's CRDs (and, for the topology operator, `rabbitmqclusters.rabbitmq.com`) are not served
([usage.md](usage.md)). The check is a named GET per CRD; offline (no `compositiondefinitions.core.krateo.io`) it is
skipped.
