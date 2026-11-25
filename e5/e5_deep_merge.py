"""把全树扫描结果并入结构层：deep_has_entry 的仓库升格为 pass_has_entry（标注 evidence=deep）。

目的：结构层不再只看顶层目录，而是看整棵树——顶层没有 tests/ 但深层有 test_*.py 的仓库，
此前被误判"无入口"。本脚本只改判定字段并重算 summary，其它字段不动。
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
STRUCT = os.path.join(ROOT, "e5_20261125", "e5_structural.json")
DEEP = os.path.join(ROOT, "e5_20261125", "e5_deep_20261125.json")

s = json.load(open(STRUCT, encoding="utf-8"))
deep = {r["repo"]: r for r in json.load(open(DEEP, encoding="utf-8"))["records"]}

promoted, selfcheck = [], []
for rec in s["records"]:
    d = deep.get(rec["repo"])
    if not d:
        continue
    rec["deep"] = {k: d.get(k) for k in ("test_files", "kinds", "samples", "truncated")}
    if d["verdict"] == "deep_has_entry" and rec["verdict"] == "pass_no_entry":
        rec["verdict"] = "pass_has_entry"
        rec["evidence_layer"] = "deep"
        rec["verification_entries"] = ["deep:" + k for k in d.get("kinds", [])] or ["deep:test-files"]
        promoted.append(rec["repo"])
    elif d["verdict"] == "deep_selfcheck_only":
        # 只有自检脚本（check_/verify_/validate/selftest）：单列，不进入 E5 合格候选
        rec["selfcheck_only"] = True
        rec["selfcheck_files"] = d.get("selfcheck_files", 0)
        rec["selfcheck_samples"] = d.get("selfcheck_samples", [])
        selfcheck.append(rec["repo"])

counts = {}
for rec in s["records"]:
    counts[rec["verdict"]] = counts.get(rec["verdict"], 0) + 1
s["summary"]["counts"] = counts
s["summary"]["measurable"] = counts.get("pass_has_entry", 0)
s["summary"]["selfcheck_only"] = len(selfcheck)
s["summary"]["note"] = ("结构实测（三层）：顶层 commit+contents；全树 recursive tree 扫描（测试/仅自检/都没有）；"
                        "仅自检脚本单列，不计入 E5 合格候选")
s["summary"]["promoted_by_deep"] = len(promoted)
s["summary"]["generated_at"] = s["summary"].get("generated_at")

json.dump(s, open(STRUCT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"promoted": promoted, "counts": counts}, ensure_ascii=False, indent=1))
