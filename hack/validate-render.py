#!/usr/bin/env python3
"""Each chart renders its upstream manifest with exactly the documented changes, the HA defaults, and its refusals.

    hack/validate-render.py [repo-root]

Per chart (hack/upstream.yaml):
  1. FAITHFUL. Rendered into a namespace other than upstream's, at the chart's defaults, the output equals what this
     script derives from the vendored upstream file on its own: every document but the Namespace, "rabbitmq-system"
     replaced by the release namespace, helm.sh/resource-policy: keep on each CRD, and the operator Deployment with
     the values' replicas, image and pod anti-affinity, plus a PodDisruptionBudget. Compared object by object, so any
     other difference (a dropped object, a changed field) fails. No "rabbitmq-system" is left.
  2. HA DEFAULTS. 2 replicas; preferred anti-affinity by hostname over the Deployment's own labels; a PDB with
     maxUnavailable 1 selecting exactly the Deployment's pods; leader election on (the topology operator's
     --leader-elect argument; the cluster-operator always elects, cmd/main.go at v2.23.2 sets LeaderElection: true,
     and ships the leader-election Role this checks for).
  3. VARIANTS. replicas 1 renders no PDB; podAntiAffinity required and none render what they say; an image
     override, resources, nodeSelector and tolerations reach the operator container and pod.
  4. REFUSALS. The chart's CRD lookup is replaced by stand-ins: with core-provider's CRD absent (offline) it renders;
     with it present and every required CRD served it renders; with any one required CRD missing it fails, naming it.
     A chart without its vendored file fails.

Fails when helm or PyYAML is missing, and when hack/upstream.yaml lists nothing.
"""
import copy
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
NS = "gate-ns"
WITNESS = "compositiondefinitions.core.krateo.io"


def measurement_failed(msg):
    print("FAILED MEASUREMENT: " + msg)
    sys.exit(2)


try:
    import yaml
except ImportError:
    measurement_failed("PyYAML unavailable, so nothing was rendered")
if shutil.which("helm") is None:
    measurement_failed("helm not on PATH, so nothing was rendered")

entries = (yaml.safe_load(open(os.path.join(ROOT, "hack", "upstream.yaml"))) or {}).get("upstreams") or []
if not entries:
    measurement_failed("hack/upstream.yaml lists no upstream, so nothing was checked")
failures = []
counts = {}


def fail(m):
    failures.append(m)


def stage(chart, tmp, name, served=None, drop_file=False):
    w = os.path.join(tmp, name)
    shutil.copytree(os.path.join(ROOT, "blueprints", chart, "chart"), w)
    cy = os.path.join(w, "Chart.yaml")
    txt = open(cy).read()
    open(cy, "w").write(txt.replace("CHART_VERSION", "0.0.0-gate"))
    if served is not None:
        p = os.path.join(w, "templates", "_preconditions.tpl")
        src = open(p).read()
        lines = [l for l in src.splitlines() if "GATE-LOOKUP" in l and "lookup " in l]
        if len(lines) != 1:
            measurement_failed("%s: _preconditions.tpl has %d GATE-LOOKUP line(s), want 1, so the refusal cannot be "
                               "driven" % (chart, len(lines)))
        stub = '{{- if has . (list %s) }}true{{ end -}}' % " ".join('"%s"' % s for s in served)
        open(p, "w").write(src.replace(lines[0], stub))
    if drop_file:
        shutil.rmtree(os.path.join(w, "files"))
    return w


def render(chart_dir, values=None):
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(values or {}, f)
    try:
        r = subprocess.run(["helm", "template", "gate", chart_dir, "--namespace", NS, "--kube-version", "1.36.0",
                            "-f", f.name], capture_output=True, text=True)
    finally:
        os.unlink(f.name)
    return r.returncode, r.stdout, r.stderr


def keyed(docs):
    return {(d["kind"], d["metadata"].get("namespace", ""), d["metadata"]["name"]): d for d in docs}


def expected(e, values):
    raw = open(os.path.join(ROOT, "blueprints", e["chart"], "chart", "files", "upstream", e["asset"])).read()
    out = []
    for d in yaml.safe_load_all(raw.replace("rabbitmq-system", NS)):
        if not d or d.get("kind") == "Namespace":
            continue
        if d["kind"] == "CustomResourceDefinition":
            d["metadata"].setdefault("annotations", {})["helm.sh/resource-policy"] = "keep"
        if d["kind"] == "Deployment":
            d["spec"]["replicas"] = values["replicas"]
            pod = d["spec"]["template"]["spec"]
            for c in pod["containers"]:
                if c["name"] == e["container"]:
                    c["image"] = "%s:%s" % (values["image"]["repository"], values["image"]["tag"])
                    if values["image"].get("pullPolicy"):
                        c["imagePullPolicy"] = values["image"]["pullPolicy"]
                    if values.get("resources"):
                        c["resources"] = values["resources"]
            labels = d["spec"]["selector"]["matchLabels"]
            term = {"labelSelector": {"matchLabels": labels}, "topologyKey": values["podAntiAffinity"]["topologyKey"]}
            t = values["podAntiAffinity"]["type"]
            if t == "preferred":
                pod["affinity"] = {"podAntiAffinity": {"preferredDuringSchedulingIgnoredDuringExecution": [
                    {"weight": 100, "podAffinityTerm": term}]}}
            elif t == "required":
                pod["affinity"] = {"podAntiAffinity": {"requiredDuringSchedulingIgnoredDuringExecution": [term]}}
            if values.get("nodeSelector"):
                pod["nodeSelector"] = values["nodeSelector"]
            if values.get("tolerations"):
                pod["tolerations"] = values["tolerations"]
            if values["replicas"] > 1:
                out.append({"apiVersion": "policy/v1", "kind": "PodDisruptionBudget",
                            "metadata": {"name": d["metadata"]["name"], "namespace": NS},
                            "spec": {"maxUnavailable": values["podDisruptionBudget"]["maxUnavailable"],
                                     "selector": {"matchLabels": labels}}})
        out.append(d)
    return out


def compare(label, chart_dir, e, overrides):
    base = yaml.safe_load(open(os.path.join(ROOT, "blueprints", e["chart"], "chart", "values.yaml")))
    values = copy.deepcopy(base)
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(values.get(k), dict):
            values[k].update(v)
        else:
            values[k] = v
    rc, out, err = render(chart_dir, overrides)
    if rc != 0:
        fail("%s: does not render: %s" % (label, err.strip()[:300]))
        return None
    if "rabbitmq-system" in out:
        fail("%s: the render still names rabbitmq-system, upstream's namespace, instead of the release's" % label)
    got, want = keyed([d for d in yaml.safe_load_all(out) if d]), keyed(expected(e, values))
    if not want:
        measurement_failed("%s: the vendored manifest yields no object" % label)
    for k in sorted(set(got) | set(want)):
        if k not in got:
            fail("%s: %s %s/%s is not rendered" % (label, *k))
        elif k not in want:
            fail("%s: %s %s/%s is rendered but is not upstream's" % (label, *k))
        elif got[k] != want[k]:
            fail("%s: %s %s/%s differs from upstream with the documented changes" % (label, *k))
    return got


def deployment(objs):
    ds = [o for o in objs.values() if o["kind"] == "Deployment"]
    return ds[0] if len(ds) == 1 else None


def main():
    with tempfile.TemporaryDirectory() as tmp:
        for e in entries:
            c = e["chart"]
            w = stage(c, tmp, c)
            got = compare("1 " + c, w, e, {})
            if got is None:
                continue
            counts[c] = len(got)
            dep = deployment(got)
            if not dep:
                fail("2 %s: not exactly one Deployment rendered" % c)
                continue
            pod = dep["spec"]["template"]["spec"]
            labels = dep["spec"]["selector"]["matchLabels"]
            pdbs = [o for o in got.values() if o["kind"] == "PodDisruptionBudget"]
            if dep["spec"].get("replicas") != 2:
                fail("2 %s: default replicas %s, want 2" % (c, dep["spec"].get("replicas")))
            pref = ((pod.get("affinity") or {}).get("podAntiAffinity") or {}).get(
                "preferredDuringSchedulingIgnoredDuringExecution") or []
            if not pref or pref[0]["podAffinityTerm"]["labelSelector"]["matchLabels"] != labels \
                    or pref[0]["podAffinityTerm"]["topologyKey"] != "kubernetes.io/hostname":
                fail("2 %s: no preferred hostname anti-affinity over the Deployment's own labels" % c)
            if len(pdbs) != 1 or pdbs[0]["spec"] != {"maxUnavailable": 1, "selector": {"matchLabels": labels}}:
                fail("2 %s: want one PDB, maxUnavailable 1, selecting the Deployment's pods; got %s"
                     % (c, [p["spec"] for p in pdbs]))
            cont = [x for x in pod["containers"] if x["name"] == e["container"]][0]
            if c == "rabbitmq-topology-operator" and "--leader-elect" not in (cont.get("args") or []):
                fail("2 %s: the operator runs without --leader-elect, so two replicas would both act" % c)
            if not any(o["kind"] == "Role" and "leader-election" in o["metadata"]["name"] for o in got.values()):
                fail("2 %s: no leader-election Role, so the replicas cannot elect a leader" % c)
            compare("3 %s replicas 1" % c, w, e, {"replicas": 1})
            compare("3 %s required" % c, w, e, {"podAntiAffinity": {"type": "required"}})
            compare("3 %s none" % c, w, e, {"podAntiAffinity": {"type": "none"}})
            compare("3 %s placement" % c, w, e, {"resources": {"requests": {"cpu": "50m"}},
                                                 "nodeSelector": {"node-role": "infra"},
                                                 "tolerations": [{"key": "infra", "operator": "Exists"}],
                                                 "image": {"repository": "registry.example/mirror/operator",
                                                           "tag": "0.0.1-gate", "pullPolicy": "IfNotPresent"}})
            needed = list(e.get("requires") or [])
            cases = [("offline (no core-provider CRD)", [], True),
                     ("live, everything served", [WITNESS] + needed, True)]
            for n in needed:
                cases.append(("live, %s absent" % n, [WITNESS] + [x for x in needed if x != n], False, n))
            for case in cases:
                label, served, ok = case[0], case[1], case[2]
                rc, _, err = render(stage(c, tmp, "%s-%d" % (c, cases.index(case)), served=served))
                if ok and rc != 0:
                    fail("4 %s: %s is refused: %s" % (c, label, err.strip()[:200]))
                if not ok:
                    if rc == 0:
                        fail("4 %s: %s renders; it must be refused" % (c, label))
                    elif case[3] not in err:
                        fail("4 %s: %s is refused without naming %s: %s" % (c, label, case[3], err.strip()[:200]))
            rc, _, err = render(stage(c, tmp, c + "-nofile", drop_file=True))
            if rc == 0 or "missing from the chart" not in err:
                fail("4 %s: without its vendored manifest it does not fail with the reason (rc %d)" % (c, rc))
    if failures:
        for f in failures:
            print("FAIL: " + f)
        sys.exit(1)
    print("OK: %s render upstream with exactly the documented changes, 2 replicas with leader election, preferred "
          "anti-affinity and a drainable PDB; variants and refusals hold"
          % ", ".join("%s (%d objects)" % (k, v) for k, v in counts.items()))


main()
