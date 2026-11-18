---
type: Usage
title: Installing the RabbitMQ operator blueprints
description: Preconditions, registering the two CompositionDefinitions, the install order, and upgrades.
resource: rabbitmq-operator
tags:
  - krateo
  - blueprint
  - rabbitmq
  - usage
timestamp: 2026-11-18T00:00:00+00:00
---
# Usage

## Preconditions

**cert-manager, from any source.** Both charts refuse to render while cert-manager's CRDs
(`certificates.cert-manager.io`, `issuers.cert-manager.io`) are not served, with the reason on the Composition's
status. They render by themselves on the next reconcile once cert-manager is installed.

- With Krateo, the installer brings cert-manager with `features.ingress`.
- Otherwise, any install works, for example:

  ```sh
  helm install cert-manager oci://quay.io/jetstack/charts/cert-manager \
    --namespace cert-manager --create-namespace --set crds.enabled=true
  ```

## Install

Register both CompositionDefinitions, then create the two Compositions (examples/basic). Each chart archive carries
its stamped CompositionDefinition at `<chart>/compositiondefinition.yaml`; `<version>` is the release:

```sh
kubectl create namespace rabbitmq-operator-system
for c in rabbitmq-cluster-operator rabbitmq-topology-operator; do
  helm pull "oci://ghcr.io/krateo-blueprints/charts/${c}" --version <version> --untar --untardir /tmp/rmqop
  kubectl apply -n rabbitmq-operator-system -f "/tmp/rmqop/${c}/compositiondefinition.yaml"
done
kubectl apply -f examples/basic/
```

**The namespace convention.** A cluster-prerequisite blueprint lives in `<name>-system`, as krateo-openstack-blueprint
lives in `openstack-system`: here `rabbitmq-operator-system`. The CompositionDefinitions are registered there, and the
example Compositions are created there too, so the operators run in it. The Composition's namespace is the release's
namespace, which replaces upstream's `rabbitmq-system` everywhere, and the operators find it at run time. Any other
namespace works the same way.

Applying both Compositions at once converges: the topology operator refuses to render until the cluster-operator has
installed RabbitmqCluster's CRD, then renders on a later reconcile.

## Upgrade

Bump the Compositions' apiVersion to the new release's served version. The CRDs carry
`helm.sh/resource-policy: keep`, so a release's removal never deletes them; a newer release replaces them with the new
upstream definitions.

## Remove

Deleting a Composition removes its operator, and keeps its CRDs and every custom resource. To remove the CRDs too,
delete them explicitly, after removing the custom resources they hold.
