"""e5_verify_all：一条命令，第三方在自己机器上比对读数。

用法：
  GH_TOKEN=<只读token> python e5_verify_all.py            # 默认抽 8 件
  GH_TOKEN=... python e5_verify_all.py --n 16
  GH_TOKEN=... python e5_verify_all.py --repos owner/a owner/b

产出：逐件 MATCH / DIFF（passed 条数是否一致、exit 是否一致），
末尾给 MATCH 率与「差在哪」的机器可读结论。退出码 0=全 MATCH，1=有 DIFF。
"""
import argparse
import io, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e5_fingerprint as fp

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
    """自执行脚本的原生判据。

    刻意不看 "FAIL" 子串：测试名里常带 FAILS_CLOSED / FAIL_FAST 这类正向名称，
    用子串判会把通过的件判成失败。只认真实失败计数与 Traceback。
    """
    up = blob.upper()
    if "TRACEBACK (MOST RECENT CALL LAST)" in up or "TRACEBACK:" in blob:
        return None
    m = re.search(r"(\d+)\s+(?:FAILED|FAILURES?)\b", up)
    if m and int(m.group(1)) > 0:
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


def entry_scripts(root):
    """入口候选：run* 优先，其次 selftest*，再次其它脚本；.py 与 .js 同等对待。

    返回 [(相对路径, 解释器)]。规则必须与基线一致，否则同树会跑出不同读数。
    """
    td = os.path.join(root, "tests")
    if not os.path.isdir(td):
        return []
    cands = []
    for f in sorted(os.listdir(td)):
        if f == "conftest.py" or not (f.endswith(".py") or f.endswith(".js")):
            continue
        low = f.lower()
        rank = 0 if low.startswith("run") else (1 if "selftest" in low else 2)
        cands.append((rank, f))
    cands.sort()
    out = []
    for _, f in cands:
        rel = "tests/" + f
        out.append((rel, "js" if f.endswith(".js") else "py"))
    return out


def token():
    t = os.environ.get("GH_TOKEN")
    if t:
        return t.strip()
    raise SystemExit("需要 GH_TOKEN（只读 repo scope 即可）")


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
    """按证据强度分层均衡抽样：A 2 / B 3 / C 2 / 薄 1（有多少取多少）。"""
    runner = json.load(open(os.path.join(E5, "e5_runner.json"), encoding="utf-8"))["records"]
    by = {"A": [], "B": [], "C": [], "D": []}
    for x in runner:
        if x["verdict"] != "pass":
            continue
        by[x.get("evidence_tier", "D")].append(x)
    out = []
    quota = {"A": 2, "B": 3, "C": 2, "D": 1}
    for t in ("A", "B", "C", "D"):
        out += by[t][: quota[t]]
    return out[:n] if n else out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--all", action="store_true", help="跑全部严格合格件（pass_strict）")
    ap.add_argument("--repos", nargs="*")
    ap.add_argument("--json", default=os.path.join(E5, "e5_verify_result.json"))
    a = ap.parse_args()
    h = {"Authorization": "token " + token(), "Accept": "application/vnd.github+json", "User-Agent": "e5-verify"}
    runner = {x["repo"]: x for x in json.load(open(os.path.join(E5, "e5_runner.json"), encoding="utf-8"))["records"]}
    # 内容指纹基线（可选）：有就比"树是否同一棵"，没有就只比 passed
    mh_path = os.path.join(E5, "e5_manifest_hashes.json")
    mh = {}
    if os.path.exists(mh_path):
        for r in json.load(open(mh_path, encoding="utf-8"))["records"]:
            if r.get("manifest_sha256"):
                mh[r["repo"]] = r["manifest_sha256"]
    if a.repos:
        picks = [runner[r] for r in a.repos if r in runner]
    elif a.all:
        picks = [x for x in runner.values() if x.get("strict_verdict") == "pass_strict"]
    else:
        picks = pick(a.n)

    print("本机 python", sys.version.split()[0], "|", sys.platform, "| 样本", len(picks), "件",
          "| 指纹基线", len(mh), "件")
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
            # 先验"树是否同一棵"，再验"跑出来是否同一份读数"
            md, nf = fp.manifest(root)
            base_h = mh.get(repo)
            if base_h is None:
                hs = "NO_BASELINE"
            elif md == base_h:
                hs = "SAME"
            else:
                hs = "DIFF"
            row.update(manifest_sha256=md, files=nf, hash_status=hs)
            tests = walk_tests(root)
            if not tests and not entry_scripts(root):
                row.update(local_passed=0, local_exit=None, status="NO_TESTS")
                rows.append(row); print("NO_TESTS", repo, flush=True); continue
            if not tests:  # 只有 .js 之类的非 pytest 入口：跳过 pytest，直接走脚本路径
                es = entry_scripts(root)
                tests = [es[0][0]] if es else []
            env = dict(os.environ); env["PYTHONPATH"] = root; env["PYTHONIOENCODING"] = "utf-8"
            # 与基线一致：有 tests/ 目录就跑目录（保留 conftest 与相对导入），否则按文件列表
            tdir = os.path.join(root, "tests")
            targets = ["tests"] if os.path.isdir(tdir) else tests
            base_cmd = [sys.executable, "-m", "pytest"] + targets + ["-q", "--maxfail=20", "-p", "no:cacheprovider"]
            p = subprocess.run(base_cmd, cwd=root, capture_output=True, text=True, timeout=900, env=env, errors="replace")
            blob = (p.stdout or "") + (p.stderr or "")
            lp = int(PASS_RE.search(blob).group(1)) if PASS_RE.search(blob) else 0
            lf = int(FAIL_RE.search(blob).group(1)) if FAIL_RE.search(blob) else 0
            le = int(ERR_RE.search(blob).group(1)) if ERR_RE.search(blob) else 0
            used = "pytest"
            # 规则一（唯一例外）：tests/ 下有 run*.js 时先用 node 跑它。
            # 理由：JS 总入口不是 pytest 能覆盖的，且此类仓库的 py 用例只是子集
            # （regdoc-commons: run.js 52 条 vs pytest 只收到 13 条 py 用例）。
            js_entry = [rel for rel, kind in entry_scripts(root)
                        if kind == "js" and os.path.basename(rel).lower().startswith("run")]
            if js_entry:
                q = subprocess.run(["node", js_entry[0]], cwd=root, capture_output=True,
                                   text=True, timeout=900, env=env, errors="replace")
                qblob = (q.stdout or "") + (q.stderr or "")
                nat = native(qblob)
                if nat and q.returncode == 0:
                    blob, p, le = qblob, q, 0
                    lp, lf = nat
                    used = "script:" + js_entry[0]
            # pytest 收不到用例（或收到 0 条）时，回落到自执行脚本；入口按 run* > selftest* > 其它 排序，
            # .js 交给 node。逐个尝试直到判出可比较的读数，避免"取字母序第一个"这种偶然入口。
            if used == "pytest" and (p.returncode in (3, 5) or "no tests ran" in blob or lp == 0):
                for rel, kind in entry_scripts(root):
                    cmd = ["node", rel] if kind == "js" else [sys.executable, rel]
                    q = subprocess.run(cmd, cwd=root, capture_output=True,
                                       text=True, timeout=900, env=env, errors="replace")
                    qblob = (q.stdout or "") + (q.stderr or "")
                    nat = native(qblob)
                    if nat:
                        nlp, nlf = nat
                    else:
                        nlp = int(PASS_RE.search(qblob).group(1)) if PASS_RE.search(qblob) else 0
                        nlf = int(FAIL_RE.search(qblob).group(1)) if FAIL_RE.search(qblob) else 0
                    if nlp == 0 and q.returncode != 0:
                        continue  # 这条入口跑不起来，试下一条
                    blob, p, lp, lf, le = qblob, q, nlp, nlf, 0
                    used = "script:" + rel
                    break
            same = (lp == row["baseline_passed"] and lf == 0 and le == 0 and p.returncode == 0)
            row.update(local_passed=lp, local_failed=lf, local_errors=le, local_exit=p.returncode,
                       entry=used, status="MATCH" if same else "DIFF",
                       tail=(p.stdout or "").strip().splitlines()[-1:])
            # 树不一致但读数一致 = 说明基线里的 commit 与仓库当前内容已经不是同一棵树
            if hs == "DIFF" and same:
                row["status"] = "MATCH_READING_TREE_DIFF"
        except Exception as e:
            row.update(status="ERROR", note="%s: %s" % (type(e).__name__, str(e)[:120]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        rows.append(row)
        print("%-9s %-22s %-45s base=%-4s local=%-4s exit=%s" % (
            row["status"], row.get("hash_status", "-"), repo, row.get("baseline_passed"),
            row.get("local_passed"), row.get("local_exit")), flush=True)

    ok = sum(1 for r in rows if r.get("status") == "MATCH")
    usable = sum(1 for r in rows if r.get("status") in ("MATCH", "DIFF", "MATCH_READING_TREE_DIFF"))
    hashed = sum(1 for r in rows if r.get("hash_status") == "SAME")
    hash_compared = sum(1 for r in rows if r.get("hash_status") in ("SAME", "DIFF"))
    tree_diff = [r["repo"] for r in rows if r.get("hash_status") == "DIFF"]
    res = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "machine": {"python": sys.version.split()[0], "platform": sys.platform},
           "sample": len(rows), "match": ok, "comparable": usable,
           "match_rate": round(ok / usable, 3) if usable else None,
           "hash_algorithm": fp.ALGO,
           "hash_compared": hash_compared, "hash_same": hashed, "tree_diff": tree_diff,
           "conclusion": ("读数一致，且树指纹逐件相同——可当同一份基线"
                          if ok == usable and usable > 0 and not tree_diff
                          else ("读数一致但树指纹有差异：" + ",".join(tree_diff)) if ok == usable and usable > 0
                          else "存在差异：先看 DIFF 行的 tail，再判断是环境还是代码"),
           "records": rows}
    json.dump(res, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "records"}, ensure_ascii=False))
    sys.exit(0 if (usable and ok == usable and not tree_diff) else 1)


if __name__ == "__main__":
    main()
