"""第四档实测：对"仅自检脚本"的仓库，真下载、真执行自检脚本，如实记 exit。

自检脚本（check_/verify_/validate/selftest）通过只说明格式/目录/链接没坏，
不证明被测代码正确，所以这一档**不计入 E5 合格**，只回答"能不能跑通"。
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

API = "https://api.github.com"
ROOT = os.path.dirname(os.path.abspath(__file__))
DEEP = os.path.join(ROOT, "e5_20261125", "e5_deep_20261125.json")
STRUCT = os.path.join(ROOT, "e5_20261125", "e5_structural.json")
OUT = os.path.join(ROOT, "e5_20261125", "e5_selfcheck.json")


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


def get_bytes(h, url, limit=140 * 1024 * 1024):
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=180) as r:
        chunks, total = [], 0
        while True:
            b = r.read(65536)
            if not b:
                break
            chunks.append(b)
            total += len(b)
            if total > limit:
                raise ValueError("too large")
    return b"".join(chunks)


def main():
    h = {"Authorization": "token " + token(),
         "Accept": "application/vnd.github+json", "User-Agent": "e5-selfcheck"}
    deep = json.load(open(DEEP, encoding="utf-8"))["records"]
    shas = {r["repo"]: r["commit"] for r in json.load(open(STRUCT, encoding="utf-8"))["records"]}
    targets = [r for r in deep if r["verdict"] == "deep_selfcheck_only"]
    recs = []
    for t in targets:
        repo, script = t["repo"], (t.get("selfcheck_samples") or [None])[0]
        out = {"repo": repo, "script": script}
        if not script:
            out.update({"verdict": "no_script"})
            recs.append(out)
            continue
        tmp = tempfile.mkdtemp(prefix="e5sc-")
        try:
            data = get_bytes(h, "%s/repos/%s/zipball/%s" % (API, repo, shas[repo]))
            zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
            tops = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
            root = os.path.join(tmp, tops[0]) if len(tops) == 1 else tmp
            if script.endswith(".py"):
                cmd = [sys.executable, script]
            elif script.endswith((".mjs", ".js", ".cjs")):
                cmd = ["node", script]
            else:
                out.update({"verdict": "skipped_shell"})
                recs.append(out)
                continue
            env = dict(os.environ)
            env["PYTHONPATH"] = root
            env["PYTHONIOENCODING"] = "utf-8"
            t0 = time.time()
            try:
                p = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                                   timeout=300, env=env, errors="replace")
                out["exit"] = p.returncode
                out["seconds"] = round(time.time() - t0, 1)
                txt = ((p.stdout or "") + (p.stderr or ""))
                out["tail"] = txt.strip().splitlines()[-4:]
                out["verdict"] = "selfcheck_ok" if p.returncode == 0 else "selfcheck_fail"
            except subprocess.TimeoutExpired:
                out["verdict"] = "selfcheck_timeout"
        except Exception as e:
            out["verdict"] = "error"
            out["detail"] = "%s: %s" % (type(e).__name__, str(e)[:130])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print(out["verdict"], repo, script, out.get("exit"), flush=True)
        recs.append(out)
    counts = {}
    for r in recs:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    summary = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "checked": len(recs),
               "counts": counts,
               "note": "自检脚本实跑；通过不计入 E5 合格，仅证明'能被外人跑通'"}
    json.dump({"summary": summary, "records": recs},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
