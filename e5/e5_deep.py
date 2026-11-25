"""E5 深层结构复核 v2：全树扫描，分三档回答"这个仓库到底能不能被外人执行验证"。

- deep_has_entry      有测试文件（test_*/spec/_test/run*/conftest）
- deep_selfcheck_only 无测试文件，但有自检脚本（check_*/verify_*/selftest/validate/smoke）——单列，不计入 E5 合格
- deep_no_entry       两者都没有

只读：不解包、不执行。输出 e5_deep_20261125.json。
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api.github.com"
ROOT = os.path.dirname(os.path.abspath(__file__))
STRUCT = os.path.join(ROOT, "e5_20261125", "e5_structural.json")
OUT = os.path.join(ROOT, "e5_20261125", "e5_deep_20261125.json")

TEST_PATTERNS = [
    ("pytest", re.compile(r"/(tests?)/test_[^/]*\.py$")),
    ("pytest", re.compile(r"(^|/)conftest\.py$")),
    ("pytest", re.compile(r"/test_[^/]*\.py$")),
    ("unittest", re.compile(r"/[^/]*_test\.py$")),
    ("node", re.compile(r"/[^/]*\.(test|spec)\.(js|mjs|cjs|ts)$")),
    ("node", re.compile(r"/tests?/[^/]*\.(test|spec)\.(js|mjs|cjs|ts)$")),
    ("runner", re.compile(r"/tests?/run[^/]*\.(py|js|mjs|sh)$")),
    ("go", re.compile(r"/[^/]*_test\.go$")),
    ("rust", re.compile(r"/tests/[^/]*\.rs$")),
]
# 自检脚本：能执行、但不是测试套件。单列，不冒充 E5 合格。
SELFCHECK_PATTERNS = [
    re.compile(r"/(check|verify|validate|selftest)[_-][^/]*\.(py|js|mjs|sh)$", re.I),
    re.compile(r"/(scripts?|tools?)/(check|verify|validate|selftest)[^/]*\.(py|js|mjs|sh)$", re.I),
    re.compile(r"/(smoke|selfcheck|self_check|self-test)[^/]*\.(py|js|mjs|sh)$", re.I),
]


def token():
    t = os.environ.get("GH_TOKEN")
    if t:
        return t.strip()
    vault = os.path.join(os.environ.get("USERPROFILE", ""), ".ucvault_local", "vault.py")
    if os.path.exists(vault):
        p = subprocess.run([sys.executable, vault, "get", "github_api_key_workflow"],
                           capture_output=True, text=True)
        return p.stdout.strip()
    return ""


def classify(paths):
    test_hits, kinds = [], set()
    for p in paths:
        for kind, rx in TEST_PATTERNS:
            if rx.search(p):
                test_hits.append(p)
                kinds.add(kind)
                break
    if test_hits:
        return "deep_has_entry", test_hits, sorted(kinds), []
    sc = [p for p in paths if any(rx.search(p) for rx in SELFCHECK_PATTERNS)]
    if sc:
        return "deep_selfcheck_only", [], [], sc
    return "deep_no_entry", [], [], []


def deep_one(item, sha):
    key = "%s/%s" % (item["owner"], item["repo"])
    rec = {"repo": key, "commit": sha}
    try:
        url = "%s/repos/%s/git/trees/%s?recursive=1" % (API, key, sha)
        req = urllib.request.Request(url, headers={
            "Authorization": "token " + token(),
            "Accept": "application/vnd.github+json",
            "User-Agent": "e5-deep"})
        with urllib.request.urlopen(req, timeout=60) as r:
            tree = json.load(r)
        rec["truncated"] = tree.get("truncated", False)
        paths = [t["path"] for t in tree.get("tree", []) if t.get("type") == "blob"]
        rec["files"] = len(paths)
        verdict, hits, kinds, sc = classify(paths)
        rec["verdict"] = verdict
        rec["test_files"] = len(hits)
        rec["kinds"] = kinds
        rec["samples"] = hits[:5] or sc[:5]
        rec["selfcheck_files"] = len(sc)
        rec["selfcheck_samples"] = sc[:3]
    except urllib.error.HTTPError as e:
        rec["verdict"] = "missing" if e.code in (403, 404) else "error"
        rec["detail"] = "HTTP %d" % e.code
    except Exception as e:
        rec["verdict"] = "error"
        rec["detail"] = "%s: %s" % (type(e).__name__, str(e)[:120])
    return rec


def main():
    d = json.load(open(STRUCT, encoding="utf-8"))
    mode = sys.argv[1] if len(sys.argv) > 1 else "--no-entry"
    if mode == "--all":
        targets = d["records"]
    elif mode == "--no-entry":
        targets = [r for r in d["records"] if r["verdict"] == "pass_no_entry"]
    else:
        targets = d["records"]
    shas = {r["repo"]: r["commit"] for r in d["records"]}
    items = [{"owner": r["repo"].split("/")[0], "repo": r["repo"].split("/")[1]} for r in targets]
    recs, t0 = [], time.time()
    with ThreadPoolExecutor(max_workers=6) as pool:
        for rec in pool.map(lambda i: deep_one(i, shas["%s/%s" % (i["owner"], i["repo"])]), items):
            recs.append(rec)
    counts = {}
    for r in recs:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    summary = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "checking": len(recs), "counts": counts,
               "seconds": round(time.time() - t0, 1),
               "note": "全树扫描三档：has_entry（测试）/ selfcheck_only（仅自检脚本，不计合格）/ no_entry"}
    json.dump({"summary": summary, "records": recs},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
