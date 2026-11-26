"""e5_verify_all：一条命令，第三方在自己机器上比对读数。

用法：
  GH_TOKEN=<只读token> python e5_verify_all.py            # 默认抽 8 件
  GH_TOKEN=... python e5_verify_all.py --n 16
  GH_TOKEN=... python e5_verify_all.py --repos owner/a owner/b
"""
import argparse
import io, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
E5 = os.path.join(ROOT, "e5_20261125")
API = "https://api.github.com"
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__", ".tox",
             "docs", "examples", "reproductions", "archive", "legacy"}
PASS_RE = re.compile(r"(\d+) passed")
FAIL_RE = re.compile(r"(\d+) failed")
ERR_RE = re.compile(r"(\d+) error")
NAT_FRAC = re.compile(r"(\d+)\s*/\s*(\d+)\s*(?:PASS|通过|passed)", re.I)
NAT_CHK = re.compile(r"PASS\s+(\d+)\s+checks", re.I)


def native(blob):
    up = blob.upper()
    if "FAIL" in up.replace("PASS", "") or "TRACEBACK" in up:
        return None
    m = NAT_FRAC.search(blob)
    if m and int(m.group(1)) == int(m.group(2)):
        return int(m.group(1)), 0
    m = NAT_CHK.search(blob)
    if m:
        return int(m.group(1)), 0
    if "自测全部通过" in blob or re.search(r"OK:", blob):
        return 1, 0
    if re.search(r"\bOK\b", blob) and "PASS" in up:
        return 1, 0
    return None


def token():
    t = os.environ.get("GH_TOKEN")
    if t:
        return t.strip()
    v = os.path.join(os.environ["USERPROFILE"], ".ucvault_local", "vault.py")
    return subprocess.run([sys.executable, v, "get", "github_api_key_workflow"], capture_output=True, text=True).stdout.strip()


def walk_tests(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if not f.endswith(".py") or f == "conftest.py":
                continue
            rel = os.path.relpath(os.path.join(dirpath, f), root).replace("\\", "/")
            if "/tests/" in "/" + rel + "/" or f.startswith("test_") or f.endswith("_test.py"):
                out.append(rel)
    return out[:40]


def download(h, repo, sha):
    req = urllib.request.Request("%s/repos/%s/zipball/%s" % (API, repo, sha), headers=h)
    with urllib.request.urlopen(req, timeout=180) as r:
        buf = []
        while True:
            b = r.read(65536)
            if not b:
                break
            buf.append(b)
    return b"".join(buf)


def pick(n):
    runner = json.load(open(os.path.join(E5, "e5_runner.json"), encoding="utf-8"))["records"]
    by = {"A": [], "B": [], "C": [], "D": []}
    for x in runner:
        if x["verdict"] != "pass":
            continue
        by[x.get("evidence_tier", "D")].append(x)
    out = []
    for t, q in (("A", 2), ("B", 3), ("C", 2), ("D", 1)):
        out += by[t][:q]
    return out[:n] if n else out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--repos", nargs="*")
    ap.add_argument("--json", default=os.path.join(E5, "e5_verify_result.json"))
    a = ap.parse_args()
    h = {"Authorization": "token " + token(), "Accept": "application/vnd.github+json", "User-Agent": "e5-verify"}
    runner = {x["repo"]: x for x in json.load(open(os.path.join(E5, "e5_runner.json"), encoding="utf-8"))["records"]}
    picks = [runner[r] for r in a.repos if r in runner] if a.repos else pick(a.n)
    print("本机 python", sys.version.split()[0], "|", sys.platform, "| 样本", len(picks), "件")
    rows = []
    for rec in picks:
        repo = rec["repo"]
        tmp = tempfile.mkdtemp(prefix="e5v-")
        row = {"repo": repo, "tier": rec.get("evidence_tier"), "commit": rec["commit"][:12],
               "baseline_passed": rec.get("passed", 0), "baseline_verdict": rec["verdict"]}
        try:
            data = download(h, repo, rec["commit"])
            zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
            tops = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
            root = os.path.join(tmp, tops[0]) if len(tops) == 1 else tmp
            tests = walk_tests(root)
            if not tests:
                row.update(local_passed=0, local_exit=None, status="NO_TESTS")
                rows.append(row); print("NO_TESTS", repo, flush=True); continue
            env = dict(os.environ); env["PYTHONPATH"] = root; env["PYTHONIOENCODING"] = "utf-8"
            tdir = os.path.join(root, "tests")
            targets = ["tests"] if os.path.isdir(tdir) else tests
            p = subprocess.run([sys.executable, "-m", "pytest"] + targets + ["-q", "--maxfail=20", "-p", "no:cacheprovider"],
                               cwd=root, capture_output=True, text=True, timeout=900, env=env, errors="replace")
            blob = (p.stdout or "") + (p.stderr or "")
            lp = int(PASS_RE.search(blob).group(1)) if PASS_RE.search(blob) else 0
            lf = int(FAIL_RE.search(blob).group(1)) if FAIL_RE.search(blob) else 0
            le = int(ERR_RE.search(blob).group(1)) if ERR_RE.search(blob) else 0
            used = "pytest"
            if p.returncode in (3, 5) or "no tests ran" in blob or lp == 0:
                scripts = [t for t in tests if os.path.basename(t).startswith("run")]
                if not scripts and os.path.isdir(tdir):
                    cand = sorted(f for f in os.listdir(tdir) if f.endswith(".py") and f != "conftest.py")
                    scripts = ["tests/" + cand[0]] if cand else []
                if scripts:
                    q = subprocess.run([sys.executable, scripts[0]], cwd=root, capture_output=True,
                                       text=True, timeout=900, env=env, errors="replace")
                    blob = (q.stdout or "") + (q.stderr or "")
                    p = q
                    used = "script:" + scripts[0]
                    nat = native(blob)
                    if nat:
                        lp, lf = nat
                    else:
                        lp = int(PASS_RE.search(blob).group(1)) if PASS_RE.search(blob) else 0
                        lf = int(FAIL_RE.search(blob).group(1)) if FAIL_RE.search(blob) else 0
                    le = 0
            same = (lp == row["baseline_passed"] and lf == 0 and le == 0 and p.returncode == 0)
            row.update(local_passed=lp, local_failed=lf, local_errors=le, local_exit=p.returncode,
                       entry=used, status="MATCH" if same else "DIFF",
                       tail=(p.stdout or "").strip().splitlines()[-1:])
        except Exception as e:
            row.update(status="ERROR", note="%s: %s" % (type(e).__name__, str(e)[:120]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        rows.append(row)
        print("%-9s %-45s base=%-5s local=%-5s exit=%s" % (
            row["status"], repo, row.get("baseline_passed"), row.get("local_passed"), row.get("local_exit")), flush=True)
    ok = sum(1 for r in rows if r.get("status") == "MATCH")
    usable = sum(1 for r in rows if r.get("status") in ("MATCH", "DIFF"))
    res = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "machine": {"python": sys.version.split()[0], "platform": sys.platform, "host": os.environ.get("COMPUTERNAME")},
           "sample": len(rows), "match": ok, "comparable": usable,
           "match_rate": round(ok / usable, 3) if usable else None,
           "conclusion": ("读数一致，可当同一份基线" if ok == usable and usable > 0
                          else "存在差异：先看 DIFF 行的 tail，再判断是环境还是代码"),
           "records": rows}
    json.dump(res, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "records"}, ensure_ascii=False))
    sys.exit(0 if (usable and ok == usable) else 1)


if __name__ == "__main__":
    main()
