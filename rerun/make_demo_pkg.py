# -*- coding: utf-8 -*-
"""make_demo_pkg.py —— 造合成验证链包（演示"第二个独立方怎么跑"，不冒充任何真实成果）

默认造 demo_pkg/（确定性 producer：两次重建应逐字节相同）；
加 --unstable 造 demo_pkg_unstable/（producer 写入当前时间 → 用来证明 determinism tier 真能分辨）。

包结构：
  <pkg>/manifest.json
  inputs/claim.json, inputs/evidence_1.txt, inputs/evidence_2.txt
  producer.py                  ← 重建器：从 inputs 重算 outputs，而不是只比哈希
  outputs/result.txt           ← 期望产物（由 producer 真跑出来的）
"""
import sys, os, json, hashlib, shutil, subprocess
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
UNSTABLE = "--unstable" in sys.argv
NAME = "demo_pkg_unstable" if UNSTABLE else "demo_pkg"
ROOT = os.path.join(HERE, NAME)

def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()

def write(rel, text):
    p = os.path.join(ROOT, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8", newline="\n").write(text)
    return p

if os.path.exists(ROOT):
    shutil.rmtree(ROOT)

claim = {"claim_id": "DEMO-01",
         "statement": "把两份证据按声明顺序拼接后取 sha256，等于 outputs/result.txt 的哈希",
         "rule": "spine = sha256(evidence_1 || evidence_2)"}
write("inputs/claim.json", json.dumps(claim, ensure_ascii=False, indent=1) + "\n")
write("inputs/evidence_1.txt", "batch A\nrecord 1: verdict=partial\nrecord 2: verdict=no_mapping\n")
write("inputs/evidence_2.txt", "batch B\nrecord 3: verdict=partial\nrecord 4: verdict=false_analog\n")

if UNSTABLE:
    prod = '''import hashlib, os, sys, datetime
root = sys.argv[1] if len(sys.argv) > 1 else "."
e1 = open(os.path.join(root, "inputs", "evidence_1.txt"), "rb").read()
e2 = open(os.path.join(root, "inputs", "evidence_2.txt"), "rb").read()
out = os.path.join(root, "outputs", "result.txt")
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w", encoding="utf-8").write(
    "spine_sha256=%s\\nmethod=sha256(evidence_1 || evidence_2)\\nbuilt_at=%s\\n"
    % (hashlib.sha256(e1 + e2).hexdigest(), datetime.datetime.now().isoformat()))
'''
else:
    prod = '''import hashlib, os, sys
root = sys.argv[1] if len(sys.argv) > 1 else "."
e1 = open(os.path.join(root, "inputs", "evidence_1.txt"), "rb").read()
e2 = open(os.path.join(root, "inputs", "evidence_2.txt"), "rb").read()
out = os.path.join(root, "outputs", "result.txt")
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w", encoding="utf-8", newline="\\n").write(
    "spine_sha256=%s\\nmethod=sha256(evidence_1 || evidence_2)\\n" % hashlib.sha256(e1 + e2).hexdigest())
'''
write("producer.py", prod)

# 真跑一次 producer 生成 outputs（这才是"重建"，不是复制）
r = subprocess.run([sys.executable, os.path.join(ROOT, "producer.py"), ROOT],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
if r.returncode != 0:
    print("producer 失败：", (r.stderr or "")[-300:]); sys.exit(2)

e1 = open(os.path.join(ROOT, "inputs/evidence_1.txt"), "rb").read()
e2 = open(os.path.join(ROOT, "inputs/evidence_2.txt"), "rb").read()
spine = hashlib.sha256(e1 + e2).hexdigest()

files = {rel: sha_file(os.path.join(ROOT, rel.replace("/", os.sep)))
         for rel in ["inputs/claim.json", "inputs/evidence_1.txt", "inputs/evidence_2.txt", "producer.py"]}
out_hash = sha_file(os.path.join(ROOT, "outputs", "result.txt"))
manifest = {
    "package_id": "DEMO-01-synthetic" + ("-unstable" if UNSTABLE else ""),
    "note": "合成演示包，用于验证复跑器与确定性分级本身；不含任何真实研究数据",
    "producer": "producer.py",
    "volatile": ["built_at"],
    "files": files,
    "steps": [
        {"n": 1, "op": "sha256_file", "path": "inputs/claim.json", "expect": files["inputs/claim.json"]},
        {"n": 2, "op": "sha256_file", "path": "inputs/evidence_1.txt", "expect": files["inputs/evidence_1.txt"]},
        {"n": 3, "op": "sha256_file", "path": "inputs/evidence_2.txt", "expect": files["inputs/evidence_2.txt"]},
        {"n": 4, "op": "sha256_file", "path": "producer.py", "expect": files["producer.py"]},
        {"n": 5, "op": "spine_hash", "paths": ["inputs/evidence_1.txt", "inputs/evidence_2.txt"], "expect": spine},
        {"n": 6, "op": "sha256_file", "path": "outputs/result.txt", "expect": out_hash},
    ],
    "expected": {"outputs/result.txt": out_hash},
}
write("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
print(f"{NAME} 已生成：", ROOT)
print("spine:", spine[:32], "…", "（outputs 由 producer 真跑生成）")
