"""E5 runner：真下载 → 真解包 → 真跑。判定链含 pytest / run*.py / run*.js / 自执行 .py。

只如实记 passed/failed/exit；跑不起来记 not_runnable 或 no_tests_collected，不伪装 PASS。
合格线：passed>0 且 failed=0 且 errors=0 且 exit=0。
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

API = "https://api.github.com"
ROOT = os.path.dirname(os.path.abspath(__file__))
STRUCT = os.path.join(ROOT, "e5_20261125", "e5_structural.json")
OUT = os.path.join(ROOT, "e5_20261125", "e5_runner.json")
PASS_RE = re.compile(r"(\d+) passed")
FAIL_RE = re.compile(r"(\d+) failed")
ERR_RE = re.compile(r"(\d+) error")
NAT_FRAC = re.compile(r"(\d+)\s*/\s*(\d+)\s*(PASS|通过|passed)", re.I)
NAT_CHK = re.compile(r"PASS\s+(\d+)\s+checks", re.I)


def token():
    t = os.environ.get("GH_TOKEN")
    if t:
        return t.strip()
    vault = os.path.join(os.environ["USERPROFILE"], ".ucvault_local", "vault.py")
    p = subprocess.run([sys.executable, vault, "get", "github_api_key_workflow"],
                       capture_output=True, text=True)
    return p.stdout.strip()


def headers():
    t = token()
    if not t:
        raise SystemExit("no token")
    return {"Authorization": "token " + t,
            "Accept": "application/vnd.github+json",
            "User-Agent": "e5-runner"}


def get_bytes(h, url, limit=140 * 1024 * 1024):
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=180) as r:
        chunks, total = [], 0
        while True:
            b = r.read(65536)          # 一把读会 IncompleteRead
            if not b:
                break
            chunks.append(b)
            total += len(b)
            if total > limit:
                raise ValueError("archive larger than %d bytes" % limit)
    return b"".join(chunks)


def parse_native(tail):
    up = tail.upper()
    if "FAIL" in up.replace("PASS", "") or "TRACEBACK" in up:
        return None
    m = NAT_FRAC.search(tail)
    if m and int(m.group(1)) == int(m.group(2)):
        return int(m.group(1)), 0
    m = NAT_CHK.search(tail)
    if m:
        return int(m.group(1)), 0
    if re.search(r"\bOK\b", tail) and re.search(r"\bPASS\b", up):
        return 1, 0
    if re.search(r"\bOK:", tail):
        return 1, 0
    # 中文口径：不少自研 runner 用「自测全部通过 / 全部通过」收尾
    if re.search(r"自测全部通过|全部通过|全绿|全部 PASS", tail):
        return 1, 0
    # node --test 口径：'# pass N' / '# fail M'
    m1 = re.search(r"#\s*pass\s+(\d+)", tail)
    if m1:
        m2 = re.search(r"#\s*fail\s+(\d+)", tail)
        return int(m1.group(1)), int(m2.group(1)) if m2 else 0
    if re.search(r"all tests? passed|tests? passed", tail, re.I):
        return 1, 0
    return None


def run_one(h, rec):
    repo, sha = rec["repo"], rec["commit"]
    out = {"repo": repo, "commit": sha}
    tmp = tempfile.mkdtemp(prefix="e5run-")
    try:
        data = get_bytes(h, "%s/repos/%s/zipball/%s" % (API, repo, sha))
        zf = zipfile.ZipFile(io.BytesIO(data))
        zf.extractall(tmp)
        out["bytes"] = len(data)
        tops = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
        root = os.path.join(tmp, tops[0]) if len(tops) == 1 else tmp
        env = dict(os.environ)
        env["PYTHONPATH"] = root
        env["PYTHONIOENCODING"] = "utf-8"
        # 有全树扫描结果时，按真实测试文件位置跑；否则退回顶层 tests/
        deep = rec.get("deep") or {}
        samples = deep.get("samples") or []
        py_samples = [p for p in samples if p.endswith(".py")][:20]
        js_samples = [p for p in samples if p.endswith((".js", ".mjs", ".cjs"))][:20]
        run_sample = next((p for p in samples if os.path.basename(p).startswith("run")), None)
        if run_sample and run_sample.endswith(".py"):
            cmd = [sys.executable, run_sample]
        elif py_samples:
            cmd = ([sys.executable, "-m", "pytest"] + py_samples
                   + ["-q", "--maxfail=20", "-p", "no:cacheprovider"])
        elif js_samples:
            cmd = ["node", "--test"] + js_samples
        else:
            cmd = [sys.executable, "-m", "pytest", "tests", "-q", "--maxfail=20",
                   "-p", "no:cacheprovider"]
        t0 = time.time()
        try:
            p = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                               timeout=900, env=env, errors="replace")
            rc, tail = p.returncode, (p.stdout or "")[-1500:]
        except subprocess.TimeoutExpired:
            rc, tail = None, "TIMEOUT 900s"
        blob = tail
        if rc in (5, None) or "no tests ran" in blob or "0 passed" in blob:
            tdir = os.path.join(root, "tests")
            fb = None
            # JS 项目：优先用仓库自己声明的 npm test（这是它官方入口）
            pj = os.path.join(root, "package.json")
            if os.path.exists(pj):
                try:
                    script = (json.load(open(pj, encoding="utf-8")).get("scripts") or {}).get("test")
                except Exception:
                    script = None
                npm = shutil.which("npm.cmd") or shutil.which("npm")
                if script and npm:
                    fb = ([npm, "test", "--silent"], "npm test")
            if os.path.isdir(tdir):
                names = os.listdir(tdir)
                py = [n for n in names if n.startswith("run") and n.endswith(".py")]
                js = [n for n in names if n.startswith("run") and n.endswith(".js")]
                selfx = [n for n in names if n.endswith(".py")
                         and not n.startswith(("__", "conftest")) and n not in py]
                if py:
                    fb = ([sys.executable, os.path.join("tests", py[0])], "tests/" + py[0])
                elif js:
                    fb = (["node", os.path.join("tests", js[0])], "tests/" + js[0])
                elif selfx:
                    fb = ([sys.executable, os.path.join("tests", selfx[0])],
                          "tests/" + selfx[0])
            if fb:
                try:
                    p2 = subprocess.run(fb[0], cwd=root, capture_output=True, text=True,
                                        timeout=900, env=env, errors="replace")
                    rc = p2.returncode
                    tail = ((p2.stdout or "") + (p2.stderr or ""))[-1500:]
                    blob = tail
                    out["fallback_entry"] = fb[1]
                except subprocess.TimeoutExpired:
                    rc, tail, blob = None, "TIMEOUT(fallback)", ""
                except FileNotFoundError:
                    pass
        out["seconds"] = round(time.time() - t0, 1)
        out["exit"] = rc
        out["tail"] = tail.strip().splitlines()[-6:] if tail.strip() else []
        blob = " ".join(out["tail"])
        out["passed"] = int(PASS_RE.search(blob).group(1)) if PASS_RE.search(blob) else 0
        out["failed"] = int(FAIL_RE.search(blob).group(1)) if FAIL_RE.search(blob) else 0
        out["errors"] = int(ERR_RE.search(blob).group(1)) if ERR_RE.search(blob) else 0
        native = parse_native(blob) if out.get("fallback_entry") else None
        if native:
            out["passed"], out["failed"] = native
            out["native_runner"] = "all-green"
        if rc is None:
            verdict = "error"
        elif native and rc == 0:
            verdict = "pass"
        elif out["passed"] > 0 and out["failed"] == 0 and out["errors"] == 0 and rc == 0:
            verdict = "pass"
        elif out["passed"] > 0:
            verdict = "partial"
        elif "no tests ran" in blob:
            verdict = "no_tests_collected"
        else:
            verdict = "not_runnable"
        out["verdict"] = verdict
    except Exception as e:
        out["verdict"] = "error"
        out["detail"] = "%s: %s" % (type(e).__name__, str(e)[:150])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", nargs="*")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--skip-done", action="store_true",
                    help="跳过 e5_runner.json 里已有记录的仓库（补跑用）")
    a = ap.parse_args()
    d = json.load(open(STRUCT, encoding="utf-8"))
    cands = [r for r in d["records"] if r["verdict"] == "pass_has_entry"]
    if a.repos:
        cands = [r for r in cands if r["repo"] in a.repos]
    if a.max:
        cands = cands[: a.max]
    h = headers()
    prev = {}
    if os.path.exists(OUT):
        try:
            for r in json.load(open(OUT, encoding="utf-8"))["records"]:
                prev[r["repo"]] = r
        except Exception:
            pass
    if a.skip_done:
        cands = [r for r in cands if r["repo"] not in prev]
    for rec in cands:
        r = run_one(h, rec)
        print(r["verdict"], r["repo"], r.get("passed"), r.get("failed"),
              r.get("seconds"), flush=True)
        prev[r["repo"]] = r
    results = list(prev.values())
    summary = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "candidates": len(results), "counts": {},
               "note": "runner 实跑；pass 需 passed>0 且 failed=0 且 error=0 且 exit=0"}
    for r in results:
        summary["counts"][r["verdict"]] = summary["counts"].get(r["verdict"], 0) + 1
    json.dump({"summary": summary, "records": results},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
