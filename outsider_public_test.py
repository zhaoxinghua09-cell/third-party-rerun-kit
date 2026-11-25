# -*- coding: utf-8 -*-
"""outsider_public_test.py —— 以"完全匿名"的方式从公开仓取件、在本机重建、再实跑。

不带任何 token，不加 Authorization 头，只用 raw.githubusercontent.com。
目的：证明三点
  1) 外人真的能拿到（不是"我本机有所以我有"）；
  2) 拿到的东西自足，能重建 demo 包；
  3) 重建后 14/14 PASS + 6/6 拦下。
"""
import sys, os, json, urllib.request, subprocess, tempfile, hashlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://raw.githubusercontent.com/zhaoxinghua09-cell/third-party-rerun-kit/main/"
FILES = ["README.md", "rerun/README.md", "rerun/verify_chain.py", "rerun/redteam.py",
         "rerun/make_demo_pkg.py", "evidence/demo_run.json", "evidence/outsider_run.json",
         "evidence/io_selftest_clean_venv.log"]

def get(rel, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(BASE + rel, headers={"User-Agent": "outsider-test/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read(), i
        except Exception as e:
            last = e
            import time
            time.sleep(1.5 * (i + 1))   # 退避：raw.githubusercontent 在国内网络会间歇重置
    raise last

work = tempfile.mkdtemp(prefix="anon_")
print("匿名取件 →", work)
ok = 0
for rel in FILES:
    try:
        b, tries = get(rel)
        p = os.path.join(work, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(b)
        print(f"  GET 200  {rel}  {len(b)} B  sha256={hashlib.sha256(b).hexdigest()[:16]}  重试{tries}次")
        ok += 1
    except Exception as e:
        print(f"  FAIL    {rel}  {type(e).__name__}: {e}")
print(f"取回 {ok}/{len(FILES)}")

py = sys.executable
r1 = subprocess.run([py, os.path.join(work, "rerun", "make_demo_pkg.py")], capture_output=True, text=True, encoding="utf-8", errors="replace")
print("\n[重建 demo 包]", (r1.stdout or "").strip().splitlines()[-1] if r1.stdout else r1.stderr[-200:])
r2 = subprocess.run([py, os.path.join(work, "rerun", "verify_chain.py"), "--pkg", os.path.join(work, "rerun", "demo_pkg")],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
print("[校验]", [l for l in r2.stdout.splitlines() if l.startswith("SUMMARY")], "exit=", r2.returncode)
r3 = subprocess.run([py, os.path.join(work, "rerun", "redteam.py")], capture_output=True, text=True, encoding="utf-8", errors="replace")
print("[红队]", [l for l in r3.stdout.splitlines() if l.startswith("SUMMARY")], "exit=", r3.returncode)
print("\nOUTSIDER_PUBLIC_TEST =", "PASS" if (ok == len(FILES) and r2.returncode == 0 and r3.returncode == 0) else "FAIL")
open(os.path.join(work, "anon_report.json"), "w", encoding="utf-8").write(json.dumps(
    {"files_ok": ok, "total": len(FILES), "verify_exit": r2.returncode, "redteam_exit": r3.returncode,
     "verify_summary": [l for l in r2.stdout.splitlines() if l.startswith("SUMMARY")],
     "redteam_summary": [l for l in r3.stdout.splitlines() if l.startswith("SUMMARY")]}, ensure_ascii=False, indent=1))
print("工作目录：", work)
