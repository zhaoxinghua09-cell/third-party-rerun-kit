"""外部审查用抽样日志：对 4 件（A/B/C/薄 各一）重新实跑，保留完整 stdout+stderr 与环境快照。

不修改 e5_runner.json，只产出独立目录，供第三方/外部 AI 复核。
"""
import io, json, os, platform, shutil, subprocess, sys, tempfile, time, urllib.request, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
E5 = os.path.join(ROOT, "e5_20261125")
OUTDIR = os.path.join(E5, "抽样日志")
API = "https://api.github.com"
PICKS = [
    ("A", "zhaoxinghua09-cell/lgd-xverify", "plenty"),
    ("B", "zhaoxinghua09-cell/lgd-skeleton", "middle"),
    ("C", "zhaoxinghua09-cell/evaluation-evidence", "low"),
    ("D", "LGD-Eval/skill-scout", "thin"),
]


def token():
    t = os.environ.get("GH_TOKEN")
    if t:
        return t.strip()
    v = os.path.join(os.environ.get("USERPROFILE", ""), ".ucvault_local", "vault.py")
    if os.path.exists(v):
        return subprocess.run([sys.executable, v, "get", "github_api_key_workflow"],
                              capture_output=True, text=True).stdout.strip()
    raise SystemExit("no token")


def env_snapshot():
    snap = {"python": sys.version.split()[0], "platform": platform.platform(),
            "machine": platform.node()}
    for mod in ("pytest", "setuptools", "requests"):
        try:
            snap[mod] = __import__(mod).__version__
        except Exception:
            snap[mod] = None
    for exe in ("node", "npm"):
        try:
            p = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20)
            snap[exe] = p.stdout.strip() or p.stderr.strip()
        except Exception:
            snap[exe] = None
    return snap


def main():
    h = {"Authorization": "token " + token(), "Accept": "application/vnd.github+json",
         "User-Agent": "e5-sample"}
    runner = {r["repo"]: r for r in json.load(open(os.path.join(E5, "e5_runner.json"), encoding="utf-8"))["records"]}
    deep = {r["repo"]: r for r in json.load(open(os.path.join(E5, "e5_deep_20261125.json"), encoding="utf-8"))["records"]}
    os.makedirs(OUTDIR, exist_ok=True)
    snap = env_snapshot()
    rows = []
    for tier, repo, band in PICKS:
        rec = runner.get(repo)
        if not rec:
            rows.append({"tier": tier, "repo": repo, "error": "no runner record"})
            continue
        tmp = tempfile.mkdtemp(prefix="e5s-")
        row = {"tier": tier, "band": band, "repo": repo, "commit": rec["commit"],
               "expected_passed": rec["passed"]}
        try:
            req = urllib.request.Request("%s/repos/%s/zipball/%s" % (API, repo, rec["commit"]), headers=h)
            with urllib.request.urlopen(req, timeout=180) as r:
                buf = []
                while True:
                    b = r.read(65536)
                    if not b:
                        break
                    buf.append(b)
            data = b"".join(buf)
            zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
            row["bytes"] = len(data)
            tops = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
            root = os.path.join(tmp, tops[0]) if len(tops) == 1 else tmp
            samples = [p for p in (deep.get(repo, {}).get("samples") or []) if p.endswith(".py")][:20]
            run_py = next((p for p in samples if os.path.basename(p).startswith("run")), None)
            if run_py:
                cmd = [sys.executable, os.path.join(root, run_py)]
            elif samples:
                cmd = [sys.executable, "-m", "pytest"] + samples + ["-q", "--maxfail=20", "-p", "no:cacheprovider"]
            else:
                cmd = [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"]
            env = dict(os.environ); env["PYTHONPATH"] = root; env["PYTHONIOENCODING"] = "utf-8"
            row["cmd"] = " ".join(cmd[1:])
            t0 = time.time()
            p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=900, env=env, errors="replace")
            row["seconds"] = round(time.time() - t0, 1)
            row["exit"] = p.returncode
            full = "=== CMD ===\n%s\n=== EXIT %s ===\n=== STDOUT ===\n%s\n=== STDERR ===\n%s\n" % (
                row["cmd"], p.returncode, p.stdout, p.stderr)
            logpath = os.path.join(OUTDIR, "%s_%s.log" % (tier, repo.replace("/", "_").replace(".", "_")))
            open(logpath, "w", encoding="utf-8").write(full)
            row["log"] = os.path.basename(logpath)
            tail = (p.stdout or "").strip().splitlines()[-4:]
            row["tail"] = tail
        except Exception as e:
            row["error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        rows.append(row)

    md = ["# E5 外部审查抽样日志（10%）", "",
          "抽样规则：34 件严格合格中按 passed 分层各取 1 件（A 多 / B 中 / C 少 / D 薄证据），共 4 件 = 11.8%。",
          "每件从 commit 锚点重新下载 zipball（无 .git、无凭证），完整 stdout/stderr 存同目录 .log，不截断。", "",
          "## 本机环境快照", "", "```json", json.dumps(snap, ensure_ascii=False, indent=1), "```", "",
          "## 抽样结果", "", "| 档 | 仓库 | commit | 预期 passed | 实测 passed | exit | 秒 | 字节 |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if "error" in r:
            md.append("| %s | %s | - | - | ERROR | - | - | - |" % (r["tier"], r["repo"]))
    md += ["", "## 逐件输出尾", ""]
    for r in rows:
        if "error" in r:
            continue
        md += ["### %s %s `%s`" % (r["tier"], r["repo"], r["commit"][:12]), "",
               "命令：`python %s`" % r.get("cmd", "?"), "", "```", "\n".join(r.get("tail") or ["(empty)"]), "```", ""]
    open(os.path.join(OUTDIR, "抽样日志汇总_20261126.md"), "w", encoding="utf-8").write("\n".join(md))
    print("done", len([r for r in rows if "error" not in r]))


if __name__ == "__main__":
    main()
