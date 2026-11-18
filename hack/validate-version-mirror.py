#!/usr/bin/env python3
"""Every place that names a version agrees with hack/upstream.yaml and with the release tag.

    hack/validate-version-mirror.py [repo-root]

Versioning here (docs/release.md): both charts carry the repository's one version, stamped from the git tag
(CHART_VERSION), and each chart's appVersion is its upstream's version. Checked per chart:
  1. Chart.yaml: version is the CHART_VERSION placeholder; appVersion is the upstream tag without its "v"; the
     krateo.io/upstream annotation names that repository and tag; sources list this repository first and the upstream.
  2. compositiondefinition.yaml: installs oci://ghcr.io/krateo-blueprints/charts/<chart> at CHART_VERSION.
  3. values.yaml: image.repository and image.tag are the recorded image at the upstream version.
  4. templates/manifests.yaml refuses without exactly the CRDs hack/upstream.yaml lists under requires.
  5. examples/basic: one Composition per chart, all at the same composition.krateo.io/v<X-Y-Z>, each of the kind
     core-provider generates from the chart name. hack/release-preflight refuses a tag other than that version.

Fails when PyYAML is missing and when hack/upstream.yaml lists nothing.
"""
import glob
import os
import re
import sys

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
REPO = "https://github.com/krateo-blueprints/rabbitmq-operator-blueprint"


def measurement_failed(msg):
    print("FAILED MEASUREMENT: " + msg)
    sys.exit(2)


try:
    import yaml
except ImportError:
    measurement_failed("PyYAML unavailable, so nothing was read")

entries = (yaml.safe_load(open(os.path.join(ROOT, "hack", "upstream.yaml"))) or {}).get("upstreams") or []
if not entries:
    measurement_failed("hack/upstream.yaml lists no upstream, so nothing was checked")
failures = []


def kind_of(chart):
    return "".join(p[:1].upper() + p[1:] for p in re.split(r"[-_]", chart))


charts = sorted(os.path.basename(os.path.dirname(os.path.dirname(p))) for p in glob.glob(os.path.join(ROOT, "blueprints", "*", "chart", "Chart.yaml")))
if sorted(e["chart"] for e in entries) != charts:
    failures.append("hack/upstream.yaml lists %s; blueprints/ holds %s" % (sorted(e["chart"] for e in entries), charts))

for e in entries:
    d = os.path.join(ROOT, "blueprints", e["chart"], "chart")
    ver = e["tag"].lstrip("v")
    cy = yaml.safe_load(open(os.path.join(d, "Chart.yaml")))
    if cy.get("version") != "CHART_VERSION":
        failures.append("%s: Chart.yaml version is %r, not the CHART_VERSION placeholder the tag stamps"
                        % (e["chart"], cy.get("version")))
    if str(cy.get("appVersion")) != ver:
        failures.append("%s: appVersion %r, upstream is %s" % (e["chart"], cy.get("appVersion"), ver))
    if (cy.get("annotations") or {}).get("krateo.io/upstream") != "%s %s" % (e["repo"], e["tag"]):
        failures.append("%s: annotation krateo.io/upstream is %r, want %r" % (
            e["chart"], (cy.get("annotations") or {}).get("krateo.io/upstream"), "%s %s" % (e["repo"], e["tag"])))
    if (cy.get("sources") or [])[:2] != [REPO, "https://github.com/" + e["repo"]]:
        failures.append("%s: sources %s, want [%s, https://github.com/%s]" % (e["chart"], cy.get("sources"), REPO,
                                                                           e["repo"]))
    cd = yaml.safe_load(open(os.path.join(ROOT, "blueprints", e["chart"], "compositiondefinition.yaml")))
    spec = (cd.get("spec") or {}).get("chart") or {}
    if spec.get("url") != "oci://ghcr.io/krateo-blueprints/charts/" + e["chart"] or spec.get("version") != "CHART_VERSION":
        failures.append("%s: its CompositionDefinition installs %s %s" % (e["chart"], spec.get("url"), spec.get("version")))
    v = yaml.safe_load(open(os.path.join(d, "values.yaml")))
    img = v.get("image") or {}
    if img.get("repository") != e["image"] or str(img.get("tag")) != ver:
        failures.append("%s: values image %s:%s, upstream deploys %s:%s" % (e["chart"], img.get("repository"),
                                                                         img.get("tag"), e["image"], ver))
    tpl = open(os.path.join(d, "templates", "manifests.yaml")).read()
    m = re.search(r'include "rabbitmq\.preconditions\.require" \(list \$ \(list ([^)]*)\)', tpl)
    got = re.findall(r'"([^"]+)"', m.group(1)) if m else None
    if got != list(e.get("requires") or []):
        failures.append("%s: manifests.yaml requires %s, hack/upstream.yaml lists %s" % (e["chart"], got, e.get("requires")))

versions = {}
for p in sorted(glob.glob(os.path.join(ROOT, "examples", "basic", "*.yaml"))):
    for doc in yaml.safe_load_all(open(p)):
        if doc and str(doc.get("apiVersion", "")).startswith("composition.krateo.io/"):
            versions.setdefault(doc["kind"], []).append(doc["apiVersion"])
want_kinds = sorted(kind_of(e["chart"]) for e in entries)
if sorted(versions) != want_kinds or any(len(v) != 1 for v in versions.values()):
    failures.append("examples/basic holds Compositions %s, want exactly one each of %s" % (versions, want_kinds))
served = {v[0] for v in versions.values()}
if len(served) > 1:
    failures.append("examples/basic names more than one version: %s. Both charts share one version." % sorted(served))
for s in served:
    if not re.fullmatch(r"composition\.krateo\.io/v\d+-\d+-\d+", s):
        failures.append("examples/basic: apiVersion %s is not composition.krateo.io/v<X-Y-Z>" % s)

if failures:
    for f in failures:
        print("FAIL: " + f)
    sys.exit(1)
print("OK: %d chart(s) mirror their upstream (%s); examples at %s"
      % (len(entries), ", ".join("%s %s" % (e["chart"], e["tag"]) for e in entries), ", ".join(sorted(served))))
