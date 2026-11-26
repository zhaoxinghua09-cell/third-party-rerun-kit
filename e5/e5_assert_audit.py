"""公司机侧断言审计：对 36 件 pass 逐件下载 zipball，全树定位测试文件，判定强/弱/无断言。

不依赖 deep 的 samples（其字段有时是任意可执行样本），改为解包后按文件名规则全树扫描：
  */tests/* 下 .py/.js/.mjs/.cjs/.ts ；test_*.py ；*_test.py ；*.test.js ；*.spec.js
跳过 .git / node_modules / venv / dist / build。

强断言 STRONG：assert <非平凡expr> / assertEqual 等 unittest 变体 / pytest.raises / expect(...).to /
  self.assert* / rust assert! ；平凡断言 assert True|1|0|None|False 不计。
状态比对 CMP：非 if/while/return/assert 开头的 == / != 。

输出 e5_20261125/e5_assert_audit_company.json
"""
import io, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
E5 = os.path.join(ROOT, "e5_20261125")
API = "https://api.github.com"
SKIP = {".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__", ".tox"}
EXT = (".py", ".js", ".mjs", ".cjs", ".ts")

TRIVIAL = re.compile(r"assert\s+(True|False|None|1|0|\"\"|'')\s*(,|$)|assertTrue\s*\(\s*True\s*\)|assertFalse\s*\(\s*False\s*\)", re.M)
STRONG = [
    (re.compile(r"assert\s+(?!True\b|False\b|None\b|1\b|0\b)\S"), "assert"),
    (re.compile(r"assert(Equal|True|False|In|NotIn|Raises|Is|IsNot|Greater|Less|AlmostEqual|Regex|CountEqual|MultiLineEqual)\s*\("), "unittest"),
    (re.compile(r"pytest\.raises\s*\("), "pytest.raises"),
    (re.compile(r"\bexpect\s*\([^)]*\)\s*\.(to|not)\b"), "expect"),
    (re.compile(r"\bself\.assert"), "self.assert"),
    (re.compile(r"\bassert_eq!|\bassert_ne!|\bassert!"), "rust"),
]
CMP = re.compile(r"[^=!<>+\-*/]==")


def token():
    t = os.environ.get("GH_TOKEN")
    if t:
        return t.strip()
    raise SystemExit("no token")


def is_test_file(rel):
    name = rel.rsplit("/", 1)[-1]
    if rel.endswith("conftest.py"):
        return False
    return ("/tests/" in "/" + rel + "/" or name.startswith("test_")
            or name.endswith(("_test.py", ".test.js", ".spec.js", ".test.mjs", ".spec.mjs")))


def collect(root):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for f in filenames:
            if not f.endswith(EXT):
                continue
            rel = os.path.relpath(os.path.join(dirpath, f), root).replace("\\", "/")
            if is_test_file(rel):
                found.append(rel)
    return found[:40]


def classify(text):
    strong, trivial, cmp_hit, samples = 0, 0, 0, []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#") or s.startswith("//"):
            continue
        if TRIVIAL.search(s):
            trivial += 1
            continue
        hit = False
        for pat, name in STRONG:
            if pat.search(s):
                strong += 1
                hit = True
                if len(samples) < 3:
                    samples.append(s[:110])
                break
        if hit:
            continue
        if CMP.search(s) and not s.startswith(("if ", "while ", "elif ", "assert")):
            cmp_hit += 1
    return strong, trivial, cmp_hit, samples


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


def main():
    h = {"Authorization": "token " + token(), "Accept": "application/vnd.github+json", "User-Agent": "e5-audit"}
    runner = json.load(open(os.path.join(E5, "e5_runner.json"), encoding="utf-8"))
    recs = []
    for r in runner["records"]:
        if r["verdict"] != "pass":
            continue
        out = {"repo": r["repo"], "passed": r["passed"], "commit": r["commit"][:12]}
        tmp = tempfile.mkdtemp(prefix="e5a-")
        try:
            data = download(h, r["repo"], r["commit"])
            zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
            tops = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
            root = os.path.join(tmp, tops[0]) if len(tops) == 1 else tmp
            files = collect(root)
            strong = trivial = cmp_hit = 0
            samples = []
            for f in files:
                try:
                    txt = open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                s, t, c, sm = classify(txt)
                strong += s; trivial += t; cmp_hit += c
                for x in sm:
                    if len(samples) < 3:
                        samples.append("%s: %s" % (f, x))
            out.update(strong=strong, trivial=trivial, cmp=cmp_hit, files_scanned=len(files),
                       samples=samples)
        except Exception as e:
            out.update(strong=0, trivial=0, cmp=0, files_scanned=0,
                       note="%s: %s" % (type(e).__name__, str(e)[:120]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        recs.append(out)
        print("OK", r["repo"], out.get("files_scanned"), out.get("strong"), out.get("trivial"), out.get("cmp"), flush=True)

    strict, thin = [], []
    for o in recs:
        ok = o["passed"] >= 3 and (o.get("strong", 0) > 0 or o.get("cmp", 0) > 0)
        (strict if ok else thin).append(o["repo"])
    summary = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "machine": "company (client:582478:3880613324794288)",
               "pass_total": len(recs), "strict": len(strict), "thin": len(thin),
               "strict_repos": strict, "thin_repos": thin,
               "rule": "passed>=3 且 (强断言>=1 或 状态比对>=1)；平凡断言(assert True/1/None)不计"}
    json.dump({"summary": summary, "records": recs},
              open(os.path.join(E5, "e5_assert_audit_company.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
