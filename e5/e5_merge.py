"""把 E5 结构实测 + runner 实跑结果回写到 artifact_manifest_20261125.json。

只回写实测得到的字段（probe / probe_evidence / probed / pending），
不改动任何人工声明的字段。原文件先备份为 .bak。
"""
import json
import os
import shutil
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
MAN = os.path.join(ROOT, "artifact_manifest_20261125.json")
STRUCT = os.path.join(ROOT, "e5_20261125", "e5_structural.json")
RUNNER = os.path.join(ROOT, "e5_20261125", "e5_runner.json")

s = json.load(open(STRUCT, encoding="utf-8"))
by_repo = {r["repo"]: r for r in s["records"]}
runs = {}
if os.path.exists(RUNNER):
    for r in json.load(open(RUNNER, encoding="utf-8"))["records"]:
        runs[r["repo"]] = r

m = json.load(open(MAN, encoding="utf-8"))
stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
probed = 0
for item in m["items"]:
    key = "%s/%s" % (item["owner"], item["repo"])
    r = by_repo.get(key)
    if not r:
        item["probe"] = "not_probed"
        continue
    probed += 1
    rp = runs.get(key)
    item["probe"] = {
        "at": stamp,
        "method": "api commit + contents(top) + pytest-runner" if rp else "api commit + contents(top)",
        "commit": r.get("commit"),
        "commit_date": r.get("commit_date"),
        "verification_entries": r.get("verification_entries", []),
        "structural": r["verdict"],
        "runner": ({k: rp.get(k) for k in ("verdict", "passed", "failed", "errors", "seconds")}
                   if rp else None),
        "tested_by": "outside (token holder, no repo rights used)",
    }
    item["probe_evidence"] = ("e5_20261125/e5_structural.json#" + key,
                              "e5_20261125/e5_runner.json#" + key) if rp else \
                             ("e5_20261125/e5_structural.json#" + key,)

m["probed"] = probed
m["pending"] = len(m["items"]) - probed
m["probe_generated_at"] = stamp
m.setdefault("notes", []).append(
    "E5 probe 2026-11-25: %d/%d probed structurally; runner executed on %d repos "
    "(any repo with passed>0 and failed=0 counts as E5 satisfied for that repo)."
    % (probed, len(m["items"]), len(runs)))

shutil.copyfile(MAN, MAN + ".bak")
json.dump(m, open(MAN, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("probed=%d pending=%d runner=%d" % (probed, m["pending"], len(runs)))
