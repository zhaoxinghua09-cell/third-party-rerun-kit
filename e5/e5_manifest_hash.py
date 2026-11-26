"""生成内容指纹基线：对严格合格件下载 zipball，逐文件 sha256 汇总成 manifest 指纹。

指纹 = sha256( 逐行 "rel_path<TAB>sha256(file)" 排序拼接 )。
作用：让复跑者不仅能比对 passed 条数，还能比对"拿到的树是不是同一棵树"。
"""
import hashlib, io, json, os, shutil, subprocess, sys, tempfile, time, urllib.request, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
E5 = os.path.join(ROOT, "e5_20261125")
API = "https://api.github.com"
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__", ".tox"}


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


def manifest(root):
    items = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, root).replace("\\", "/")
            try:
                with open(p, "rb") as fh:
                    h256 = hashlib.sha256(fh.read()).hexdigest()
            except Exception:
                h256 = "UNREADABLE"
            items.append("%s\t%s" % (rel, h256))
    items.sort()
    digest = hashlib.sha256("\n".join(items).encode()).hexdigest()
    return digest, len(items)


def main():
    h = {"Authorization": "token " + token(), "Accept": "application/vnd.github+json", "User-Agent": "e5-mh"}
    runner = [x for x in json.load(open(os.path.join(E5, "e5_runner.json"), encoding="utf-8"))["records"]
              if x.get("strict_verdict") == "pass_strict"]
    out = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "machine": "company (client:582478:3880613324794288)",
           "algorithm": "sha256 over sorted lines 'rel_path\\tsha256(file)'",
           "records": []}
    for rec in runner:
        tmp = tempfile.mkdtemp(prefix="e5mh-")
        row = {"repo": rec["repo"], "commit": rec["commit"]}
        try:
            data = download(h, rec["repo"], rec["commit"])
            zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
            tops = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
            root = os.path.join(tmp, tops[0]) if len(tops) == 1 else tmp
            digest, files = manifest(root)
            row.update(manifest_sha256=digest, files=files, zip_bytes=len(data))
            print("OK  %-45s files=%-5s %s" % (rec["repo"], files, digest[:16]), flush=True)
        except Exception as e:
            row.update(error="%s: %s" % (type(e).__name__, str(e)[:120]))
            print("ERR", rec["repo"], row["error"], flush=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        out["records"].append(row)
    out["total"] = len(out["records"])
    out["ok"] = sum(1 for r in out["records"] if r.get("manifest_sha256"))
    json.dump(out, open(os.path.join(E5, "e5_manifest_hashes.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("done", out["ok"], "/", out["total"])


if __name__ == "__main__":
    main()
