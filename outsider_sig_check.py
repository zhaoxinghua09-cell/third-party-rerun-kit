# -*- coding: utf-8 -*-
"""outsider_sig_check.py —— 匿名取回签名包，在"本解释器"的环境下判一次

用法：用不同解释器各跑一次，观察同包不同判：
  python outsider_sig_check.py        （有 cryptography → 应为 PASS/0）
  .venv_outsider\\Scripts\\python.exe outsider_sig_check.py （无 → 应为 INCOMPLETE/4）
"""
import sys, os, json, urllib.request, subprocess, tempfile, shutil, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://raw.githubusercontent.com/zhaoxinghua09-cell/third-party-rerun-kit/main/"
NEED = ["rerun/verify_chain.py", "trust/ed25519.pub",
        "rerun/demo_pkg_signed/manifest.json", "rerun/demo_pkg_signed/outputs/result.txt",
        "rerun/demo_pkg_signed/attest/result.sig.json",
        "rerun/demo_pkg_signed/inputs/claim.json",
        "rerun/demo_pkg_signed/inputs/evidence_1.txt",
        "rerun/demo_pkg_signed/inputs/evidence_2.txt",
        "rerun/demo_pkg_signed/producer.py"]

def get(rel, tries=4):
    # 用 GitHub contents API（匿名，Accept: raw）取件：raw.githubusercontent 有 CDN 缓存，
    # 刚推的文件会拿到旧 blob；API 返回的是当前 main 的真实内容。
    import time as _t
    api = f"https://api.github.com/repos/zhaoxinghua09-cell/third-party-rerun-kit/contents/{rel}?ref=main"
    for i in range(tries):
        try:
            req = urllib.request.Request(api, headers={"User-Agent": "outsider-sig/1.0",
                                                       "Accept": "application/vnd.github.raw"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception:
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(rel)

work = tempfile.mkdtemp(prefix="sig_")
for rel in NEED:
    p = os.path.join(work, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(get(rel))
print(f"取件 {len(NEED)}/{len(NEED)} → {work}")

has_crypto = True
try:
    import cryptography  # noqa
except Exception:
    has_crypto = False
print("本解释器 cryptography:", has_crypto)

r = subprocess.run([sys.executable, os.path.join(work, "rerun", "verify_chain.py"),
                    "--pkg", os.path.join(work, "rerun", "demo_pkg_signed")],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
for l in r.stdout.splitlines():
    if l.startswith(("[PASS]", "[FAIL]", "[INCOMPLETE]", "SUMMARY")):
        print(l)
print("\nOUTSIDER_SIG_VERDICT exit=", r.returncode, " 期望：", "0(PASS)" if has_crypto else "4(INCOMPLETE)")
ok = (r.returncode == 0) if has_crypto else (r.returncode == 4)
print("MATCHES_EXPECTATION =", ok)
shutil.rmtree(work, ignore_errors=True)
sys.exit(0 if ok else 3)
