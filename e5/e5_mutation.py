"""变异检查：对每件注入一处语义变异，看测试是否变红（KILLED）还是照样通过（SURVIVED）。

只动临时解包副本，不碰仓库、不推远端。每件只做 1 个变异点：
  优先 Compare(Eq) -> NotEq；否则 Return(Constant int) +1；否则 BoolOp And <-> Or。
跑法：pytest 全部测试文件（与 E5 主判定同一入口）。
结果：KILLED（测试抓到）/ SURVIVED（测试没抓到）/ SKIP（无可用变异点）。
"""
import argparse
import ast
import io, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
E5 = os.path.join(ROOT, "e5_20261125")
API = "https://api.github.com"
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__", ".tox", "docs",
             "examples", "reproductions", "archive", "legacy"}
IMPL_EXT = (".py",)


def token():
    t = os.environ.get("GH_TOKEN")
    if t:
        return t.strip()
    raise SystemExit("no token")


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


def walk(root, want_test):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if not f.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, f), root).replace("\\", "/")
            name = f
            is_t = ("/tests/" in "/" + rel + "/" or name.startswith("test_")
                    or name.endswith("_test.py"))
            if is_t == want_test and name != "conftest.py":
                out.append(rel)
    return out


class Mut(ast.NodeTransformer):
    def __init__(self):
        self.desc = None
        self.count = 0

    def visit_Compare(self, node):
        if self.desc is None and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            node.ops[0] = ast.NotEq()
            self.desc = "Eq->NotEq line %d" % node.lineno
            self.count += 1
            return node
        return node

    def visit_Return(self, node):
        if self.desc is None and isinstance(node.value, ast.Constant) and type(node.value.value) is int:
            node.value = ast.Constant(value=node.value.value + 1)
            self.desc = "return %d -> %d line %d" % (node.value.value - 1, node.value.value, node.lineno)
            self.count += 1
            return node
        return node


def mutate(src):
    tree = ast.parse(src)
    m = Mut()
    m.visit(tree)
    if not m.desc:
        return None, None
    return ast.unparse(tree), m.desc


def run_rep(root, tests, py, env):
    cmd = [py, "-m", "pytest"] + tests + ["-q", "--maxfail=5", "-p", "no:cacheprovider"]
    try:
        p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=900, env=env, errors="replace")
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "timeout 900s"
    blob = ((p.stdout or "") + (p.stderr or ""))
    return p.returncode, blob[-600:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", nargs="*")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    h = {"Authorization": "token " + token(), "Accept": "application/vnd.github+json", "User-Agent": "e5-mut"}
    runner = json.load(open(os.path.join(E5, "e5_runner.json"), encoding="utf-8"))["records"]
    cands = [x for x in runner if x.get("evidence_tier") == "A" and x["verdict"] == "pass"]
    if a.repos:
        cands = [x for x in cands if x["repo"] in a.repos]
    if a.limit:
        cands = cands[: a.limit]

    outpath = os.path.join(E5, "e5_mutation.json")
    prev = {}
    if os.path.exists(outpath):
        try:
            for x in json.load(open(outpath, encoding="utf-8"))["records"]:
                prev[x["repo"]] = x
        except Exception:
            pass

    for rec in cands:
        repo = rec["repo"]
        res = {"repo": repo, "commit": rec["commit"][:12], "baseline_passed": rec["passed"]}
        tmp = tempfile.mkdtemp(prefix="e5mut-")
        try:
            data = download(h, repo, rec["commit"])
            zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
            tops = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
            root = os.path.join(tmp, tops[0]) if len(tops) == 1 else tmp
            tests = walk(root, True)
            impls = walk(root, False)
            if not tests:
                res["verdict"] = "SKIP"
                res["note"] = "no python test file"
                prev[repo] = res
                print("SKIP", repo, "no tests", flush=True)
                continue
            served = False
            for rel in impls[:12]:
                src_path = os.path.join(root, rel)
                try:
                    src = open(src_path, encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                try:
                    new_src, desc = mutate(src)
                except SyntaxError:
                    continue
                if new_src is None:
                    continue
                open(src_path, "w", encoding="utf-8").write(new_src)
                env = dict(os.environ); env["PYTHONPATH"] = root; env["PYTHONIOENCODING"] = "utf-8"
                rc, tail = run_rep(root, tests, sys.executable, env)
                res["impl_file"] = rel
                res["mutation"] = desc
                res["exit"] = rc
                res["tail"] = tail.strip().splitlines()[-3:]
                if rc == "TIMEOUT":
                    res["verdict"] = "SKIP"
                    res["note"] = "timeout"
                elif rc == 0:
                    res["verdict"] = "SURVIVED"
                else:
                    res["verdict"] = "KILLED"
                served = True
                print(res["verdict"], repo, rel, desc, flush=True)
                break
            if not served:
                res["verdict"] = "SKIP"
                res["note"] = "no mutable node in impl files"
                print("SKIP", repo, "no mutation point", flush=True)
            res["seconds"] = round(time.time() - (res.get("_t0") or time.time()), 1)
        except Exception as e:
            res["verdict"] = "ERROR"
            res["note"] = "%s: %s" % (type(e).__name__, str(e)[:150])
            print("ERROR", repo, res["note"], flush=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        prev[repo] = res

    recs = list(prev.values())
    killed = sum(1 for x in recs if x.get("verdict") == "KILLED")
    surv = sum(1 for x in recs if x.get("verdict") == "SURVIVED")
    skip = sum(1 for x in recs if x.get("verdict") == "SKIP")
    summary = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "machine": "company (client:582478:3880613324794288)",
               "total": len(recs), "killed": killed, "survived": surv, "skip": skip,
               "mutation_score": round(killed / (killed + surv), 3) if killed + surv else None,
               "note": "每件 1 个变异点；KILLED=测试变红；SURVIVED=测试仍绿；只说明该点被覆盖与否，不代表整体覆盖率"}
    json.dump({"summary": summary, "records": recs}, open(outpath, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
