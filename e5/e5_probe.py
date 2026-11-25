"""E5 结构实测：162 件 GitHub 仓库，用 API 通道独立取证据（不依赖本地工作副本）。

E5 的合格线是"非协作者 clone/install 成功 + passed>0 + failed=0"。本脚本只做其中
可自动完成的两段：拿到 commit 哈希、拿到整包（zipball）并判定有没有可执行验证入口。
"passed>0" 这一段需要真的跑起来，脚本记 measurable=true 后由 runner 单独执行。

判定口径（写死，不许事后解释）：
  pass_no_entry   仓库能取到、但没有任何可执行验证入口 → E5 无法成立（记缺陷）
  pass_has_entry  仓库能取到、有 tests/ 或 pytest 配置 → 可交给 runner 实跑
  missing         404／无权限
  error           取不到（网络或大小）

用法：
    python e5_probe.py --manifest artifact_manifest_20261125.json --out e5_20261125
"""

import argparse
import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

API = "https://api.github.com"


def token():
    vault = os.path.join(os.environ["USERPROFILE"], ".ucvault_local", "vault.py")
    out = subprocess.run([sys.executable, vault, "get", "github_api_key_workflow"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit("vault 取凭据失败（不打印内容）")
    return out.stdout.strip().splitlines()[-1].strip()


def get_json(headers, url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8")), r.headers.get("x-ratelimit-remaining")


def get_bytes(headers, url, limit=40 * 1024 * 1024):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=90) as r:
        chunks, total = [], 0
        while True:
            b = r.read(65536)          # 大包用 urllib 一把读会 IncompleteRead
            if not b:
                break
            chunks.append(b)
            total += len(b)
            if total > limit:
                raise ValueError("archive larger than %d bytes" % limit)
    return b"".join(chunks)


def probe_one(headers, item, deep=False):
    owner, repo = item["owner"], item["repo"]
    base = "%s/repos/%s/%s" % (API, owner, repo)
    rec = {"repo": "%s/%s" % (owner, repo), "visibility": item.get("visibility")}
    try:
        commit, rem = get_json(headers, base + "/commits?per_page=1")
        sha = commit[0]["sha"]
        date = commit[0]["commit"]["committer"]["date"]
        rec.update({"commit": sha, "commit_date": date, "rate": rem})

        tree, _ = get_json(headers, base + "/contents?ref=" + sha)
        names = [t.get("name") for t in tree if isinstance(t, dict)]
        kinds = {t.get("name"): t.get("type") for t in tree if isinstance(t, dict)}
        rec["top_entries"] = len(names)
        entries = []
        if kinds.get("tests") == "dir":
            entries.append("tests/")
        if kinds.get("test") == "dir":
            entries.append("test/")
        for cfg in ("pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini",
                    "package.json", "Makefile"):
            if cfg in names:
                entries.append(cfg)

        if deep:
            data = get_bytes(headers, base + "/zipball/" + sha)
            zf = zipfile.ZipFile(io.BytesIO(data))
            znames = zf.namelist()
            rec["bytes"] = len(data)
            rec["files"] = len([n for n in znames if not n.endswith("/")])
            if any("/tests/" in n for n in znames) and "tests/" not in entries:
                entries.append("tests/(nested)")

        rec["verification_entries"] = entries
        rec["measurable"] = bool(entries)
        rec["verdict"] = "pass_has_entry" if entries else "pass_no_entry"
    except urllib.error.HTTPError as e:
        rec["verdict"] = "missing" if e.code in (403, 404) else "error"
        rec["detail"] = "HTTP %d" % e.code
    except Exception as e:
        rec["verdict"] = "error"
        rec["detail"] = "%s: %s" % (type(e).__name__, str(e)[:120])
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="artifact_manifest_20261125.json")
    ap.add_argument("--out", default="e5_20261125")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--deep", action="store_true",
                    help="also download the archive (slow; only for the few that matter)")
    args = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, args.manifest), encoding="utf-8") as fh:
        manifest = json.load(fh)
    items = manifest.get("items") or manifest["artifacts"]
    if args.limit:
        items = items[: args.limit]

    tok = token()
    headers = {"Authorization": "Bearer " + tok, "User-Agent": "uibc-e5-probe",
               "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}

    outdir = os.path.join(here, args.out)
    os.makedirs(outdir, exist_ok=True)
    recs = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for rec in pool.map(lambda i: probe_one(headers, i, args.deep), items):
            recs.append(rec)
            print("%-12s %s" % (rec["verdict"], rec["repo"]), flush=True)

    counts = {}
    for r in recs:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    summary = {"generated_at": manifest.get("generated_at"),
               "probed": len(recs), "counts": counts,
               "measurable": sum(1 for r in recs if r.get("measurable")),
               "note": "结构实测：commit + 整包 + 验证入口判定。"
                       "E5 的 passed>0/failed=0 需 runner 另跑，未在本文件中计。"}
    with open(os.path.join(outdir, "e5_structural.json"), "w",
              encoding="utf-8", newline="\n") as fh:
        json.dump({"summary": summary, "records": recs}, fh,
                  ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
