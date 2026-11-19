#!/usr/bin/env python3
"""Each chart vendors its upstream release manifest unchanged.

    hack/validate-vendored.py [repo-root] [--live]

Each chart renders blueprints/<chart>/chart/files/upstream/<asset>, the release asset of the upstream tag named in
hack/upstream.yaml. Every change this repository makes is applied at render time, in templates/manifests.yaml, where
hack/validate-render.py checks it. So the vendored file itself must stay byte for byte what upstream released:
  1. its SHA-256 is the digest recorded in hack/upstream.yaml;
  2. --live (CI): it is byte-equal to the asset GitHub serves for that tag today, so a pin to the wrong tag, or an
     asset edited after vendoring, cannot pass on a recorded digest alone;
  3. its operator Deployment has the recorded container, and that container runs the recorded image at the tag's
     version, which is the image the chart's values default to (hack/validate-version-mirror.py).

The upstream's own license and notice files are vendored the same way, beside the asset (`notices` in
hack/upstream.yaml): each has its recorded SHA-256, and with --live is byte-equal to the file in the upstream repository
at the tag. The repository's NOTICE names each upstream's repository, tag and license, and the files it ships, and
LICENSE is the Apache License 2.0 that covers this repository's own work.

Fails when PyYAML is missing, when hack/upstream.yaml lists nothing, and, with --live, when GitHub cannot be read.
"""
import hashlib
import os
import sys
import urllib.request

args = [a for a in sys.argv[1:] if not a.startswith("--")]
ROOT = os.path.abspath(args[0] if args else ".")
LIVE = "--live" in sys.argv


def measurement_failed(msg):
    print("FAILED MEASUREMENT: " + msg)
    sys.exit(2)


try:
    import yaml
except ImportError:
    measurement_failed("PyYAML unavailable, so the vendored manifests were never read")

entries = (yaml.safe_load(open(os.path.join(ROOT, "hack", "upstream.yaml"))) or {}).get("upstreams") or []
if not entries:
    measurement_failed("hack/upstream.yaml lists no upstream, so nothing was checked")

failures = []
checked_notices = []
lic = os.path.join(ROOT, "LICENSE")
if not os.path.isfile(lic) or "Apache License" not in open(lic).read(2000) or "Version 2.0" not in open(lic).read(2000):
    failures.append("LICENSE is missing or is not the Apache License 2.0 that covers this repository's own work")
for e in entries:
    path = os.path.join(ROOT, "blueprints", e["chart"], "chart", "files", "upstream", e["asset"])
    if not os.path.isfile(path):
        failures.append("%s: %s is missing" % (e["chart"], os.path.relpath(path, ROOT)))
        continue
    data = open(path, "rb").read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != e["sha256"]:
        failures.append("%s: %s has SHA-256 %s, hack/upstream.yaml records %s. Re-vendor it from %s %s unchanged, or "
                        "record the new digest together with the new tag." % (e["chart"], e["asset"], digest,
                                                                            e["sha256"], e["repo"], e["tag"]))
    if LIVE:
        url = "https://github.com/%s/releases/download/%s/%s" % (e["repo"], e["tag"], e["asset"])
        try:
            served = urllib.request.urlopen(url, timeout=60).read()
        except Exception as ex:
            measurement_failed("could not read %s: %s" % (url, ex))
        if served != data:
            failures.append("%s: %s differs from what %s serves today (SHA-256 %s)"
                            % (e["chart"], e["asset"], url, hashlib.sha256(served).hexdigest()))
    want_image = "%s:%s" % (e["image"], e["tag"].lstrip("v"))
    images = []
    for d in yaml.safe_load_all(data):
        if d and d.get("kind") == "Deployment":
            for c in d["spec"]["template"]["spec"].get("containers") or []:
                if c.get("name") == e["container"]:
                    images.append(c.get("image"))
    if images != [want_image]:
        failures.append("%s: the vendored Deployment's %s container runs %s, want exactly [%s]"
                        % (e["chart"], e["container"], images or "nothing", want_image))
    notices = e.get("notices") or []
    if not e.get("license") or not any(n.get("file", "").upper().startswith("LICENSE") for n in notices):
        failures.append("%s: hack/upstream.yaml records no license and LICENSE file for %s %s; the vendored manifest is "
                        "redistributed under upstream's license, which must ship beside it" % (e["chart"], e["repo"],
                                                                                           e["tag"]))
    for n in notices:
        npath = os.path.join(ROOT, "blueprints", e["chart"], "chart", "files", "upstream", n["file"])
        if not os.path.isfile(npath):
            failures.append("%s: %s is missing" % (e["chart"], os.path.relpath(npath, ROOT)))
            continue
        ndata = open(npath, "rb").read()
        nd = hashlib.sha256(ndata).hexdigest()
        if nd != n.get("digest"):
            failures.append("%s: %s has SHA-256 %s, hack/upstream.yaml records %s" % (e["chart"], n["file"], nd,
                                                                                    n.get("digest")))
        if LIVE:
            url = "https://raw.githubusercontent.com/%s/%s/%s" % (e["repo"], e["tag"], n["file"])
            try:
                served = urllib.request.urlopen(url, timeout=60).read()
            except Exception as ex:
                measurement_failed("could not read %s: %s" % (url, ex))
            if served != ndata:
                failures.append("%s: %s differs from %s (SHA-256 %s)" % (e["chart"], n["file"], url,
                                                                       hashlib.sha256(served).hexdigest()))
        checked_notices.append(n["file"])
    notice = os.path.join(ROOT, "NOTICE")
    text = open(notice).read() if os.path.isfile(notice) else ""
    for want in ("github.com/%s/tree/%s" % (e["repo"], e["tag"]), e.get("license") or "(no license recorded)",
                 "blueprints/%s/chart/files/upstream/%s" % (e["chart"], e["asset"])) + tuple(
            "blueprints/%s/chart/files/upstream/%s" % (e["chart"], n["file"]) for n in notices):
        if want not in text:
            failures.append("%s: NOTICE does not name %s" % (e["chart"], want))

if failures:
    for f in failures:
        print("FAIL: " + f)
    sys.exit(1)
if not checked_notices:
    measurement_failed("no upstream license or notice file was checked")
print("OK: %d vendored manifest(s) match their recorded digest%s and run the recorded image (%s); %d upstream license/"
      "notice file(s) match theirs%s; NOTICE names each upstream, LICENSE is Apache-2.0"
      % (len(entries), " and the asset GitHub serves" if LIVE else "",
         ", ".join("%s %s" % (e["repo"], e["tag"]) for e in entries), len(checked_notices),
         " and the repository at the tag" if LIVE else ""))
