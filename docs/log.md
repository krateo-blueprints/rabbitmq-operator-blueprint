---
type: Log
title: rabbitmq-operator-blueprint changelog
description: Notable changes to the RabbitMQ operator blueprints, with the measurements behind each decision.
resource: rabbitmq-operator
tags:
  - krateo
  - blueprint
  - rabbitmq
  - log
timestamp: 2026-11-18T00:00:00+00:00
---
# Log

## 0.1.0 (initial)

- **Two blueprints, vendoring the upstream release manifests** of rabbitmq/cluster-operator v2.23.2 and
  rabbitmq/messaging-topology-operator v1.20.5. Neither project publishes an official Helm chart (checked at both
  tags, 2026-11-18). The asset `messaging-topology-operator-with-certmanager.yaml` is byte-identical to
  `messaging-topology-operator.yaml` at v1.20.5.
- **cert-manager is a precondition for both.** At v2.23.2 the cluster-operator manifest also carries cert-manager
  Certificates, an Issuer and CA-injected webhooks, so both charts refuse without cert-manager's CRDs.
- **The CRDs are kept on release removal** (`helm.sh/resource-policy: keep`), which upstream does not set.
- **HA by default:** 2 replicas with leader election, preferred hostname anti-affinity, a PDB.
- **One version line** for both charts ([release.md](release.md)).
- **Releases** run the org's release preflight (krateo-blueprints/charts 1.1.0) before publishing anything.
- **Namespace convention:** cluster-prerequisite blueprints live in `<name>-system`; the CompositionDefinitions and
  the example Compositions use `rabbitmq-operator-system`.
- **Every workflow `uses:` is pinned by full commit SHA** with a version comment, actions and reusable workflows alike
  (`krateo-platformops/.github` has no tags, so its pin names the commit date). `hack/validate-release-wiring.py`
  refuses a movable ref.
- **A pre-release channel** (`prerelease.yaml`, dispatched with a `ref`) publishes both charts to GHCR at
  `X.Y.Z-main.g<sha7>` (`-dev.` off main) with the stamped CompositionDefinitions and examples as a run artifact, so
  the #309 H2 live tests install a commit before any tag. It holds `contents: read` + `packages: write` only and never
  touches the Marketplace index; `hack/validate-prerelease-channel.py` checks that with mutations.
