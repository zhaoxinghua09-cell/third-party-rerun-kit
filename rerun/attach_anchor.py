# -*- coding: utf-8 -*-
"""attach_anchor.py —— 把 anchor.json 放进签名包并挂到 manifest，然后重验

顺序说明（很重要）：锚必须在公钥**已公开**之后才能生成，所以流程是
  签名 → 推公钥 → 生成锚 → 把锚塞回包里 → 再推包 → 联机核对
"""
import sys, os, json, shutil, hashlib, subprocess
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "demo_pkg_signed")
ANCHOR = os.path.join(HERE, "anchor.json")

def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()

rel = "attest/anchor.json"
dst = os.path.join(PKG, rel.replace("/", os.sep))
os.makedirs(os.path.dirname(dst), exist_ok=True)
shutil.copy(ANCHOR, dst)

m = json.load(open(os.path.join(PKG, "manifest.json"), encoding="utf-8"))
m["files"][rel] = sha_file(dst)
m["steps"].append({"n": len(m["steps"]) + 1, "op": "sha256_file", "path": rel, "expect": m["files"][rel]})
m["signature"]["anchor"] = rel
json.dump(m, open(os.path.join(PKG, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

for online in ([], ["--online"]):
    r = subprocess.run([sys.executable, os.path.join(HERE, "verify_chain.py"), "--pkg", PKG,
                        "--json", os.path.join(HERE, "signed_run.json" if not online else "signed_run_online.json")] + online,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(f"\nverify_chain{' --online' if online else ''} exit=", r.returncode)
    for l in r.stdout.splitlines():
        if l.startswith(("[PASS]", "[FAIL]", "[INCOMPLETE]", "[INFO]", "SUMMARY")):
            print(l)
