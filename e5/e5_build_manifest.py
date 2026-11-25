"""重建 E5 探测清单：三账号全量仓库，翻页到底（不设上限）。

旧清单 162 件是单页枚举的漏收结果；本脚本按 API 实际结果写入 254 件，
原清单先备份为 .bak_162。
"""
import json
import os
import shutil
import time
import urllib.request

API = "https://api.github.com"
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "artifact_manifest_20261125.json")
OWNERS = ["zhaoxinghua09-cell", "stevenzhao07", "LGD-Eval"]


def token():
    t = os.environ.get("GH_TOKEN")
    if t:
        return t.strip()
    import subprocess
    vault = os.path.join(os.environ["USERPROFILE"], ".ucvault_local", "vault.py")
    p = subprocess.run([os.sys.executable, vault, "get", "github_api_key_workflow"],
                       capture_output=True, text=True)
    return p.stdout.strip()


def h():
    return {"Authorization": "token " + token(),
            "Accept": "application/vnd.github+json",
            "User-Agent": "e5-manifest"}


def all_repos(owner):
    out, page = [], 1
    while True:
        url = "%s/users/%s/repos?per_page=100&page=%d&sort=updated" % (API, owner, page)
        req = urllib.request.Request(url, headers=h())
        with urllib.request.urlopen(req, timeout=40) as r:
            batch = json.load(r)
        if not batch:
            break
        out += batch
        if len(batch) < 100:
            break
        page += 1
    return out


def main():
    items, counts = [], {}
    for owner in OWNERS:
        repos = all_repos(owner)
        counts[owner] = len(repos)
        for r in repos:
            items.append({
                "owner": owner, "repo": r["name"],
                "visibility": "private" if r.get("private") else "public",
                "default_branch": r.get("default_branch"),
                "updated_at": r.get("updated_at"),
                "archived": r.get("archived", False),
                "probe": "not_probed", "probe_evidence": None,
            })
    m = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "generated_on": os.environ.get("COMPUTERNAME", "unknown"),
        "owners": OWNERS, "per_owner": counts, "total": len(items),
        "probed": 0, "pending": len(items),
        "notes": [
            "枚举口径：三账号全部仓库（含归档），翻页到底，不设上限。",
            "旧版 162 件为单页漏收，本版以 per_owner 为准。",
        ],
        "items": items,
    }
    if os.path.exists(OUT):
        shutil.copyfile(OUT, OUT + ".bak_162")
    json.dump(m, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"per_owner": counts, "total": len(items)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
