# -*- coding: utf-8 -*-
"""make_demo_pkg.py —— 造一个合成验证链包（用于演示"第二个独立方怎么跑"，不冒充任何真实成果）

包结构：
  demo_pkg/manifest.json
  demo_pkg/inputs/claim.json        待验证的主张（结构化）
  demo_pkg/inputs/evidence_1.txt    证据一（原始记录片段）
  demo_pkg/inputs/evidence_2.txt    证据二（原始记录片段）
  demo_pkg/outputs/result.txt       期望输出（由 evidence 按声明规则拼出）
"""
import sys, os, json, hashlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_pkg")

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

claim = {
    "claim_id": "DEMO-01",
    "statement": "把两份证据按声明顺序拼接后取 sha256，等于 outputs/result.txt 的哈希",
    "rule": "spine = sha256(evidence_1 || evidence_2)",
}
write("inputs/claim.json", json.dumps(claim, ensure_ascii=False, indent=1) + "\n")
write("inputs/evidence_1.txt", "batch A\nrecord 1: verdict=partial\nrecord 2: verdict=no_mapping\n")
write("inputs/evidence_2.txt", "batch B\nrecord 3: verdict=partial\nrecord 4: verdict=false_analog\n")

# 期望输出 = 两份证据拼接后的哈希（这是"可复算的结论"，不是叙述）
e1 = open(os.path.join(ROOT, "inputs/evidence_1.txt"), "rb").read()
e2 = open(os.path.join(ROOT, "inputs/evidence_2.txt"), "rb").read()
spine = hashlib.sha256(e1 + e2).hexdigest()
write("outputs/result.txt", f"spine_sha256={spine}\nmethod=sha256(evidence_1 || evidence_2)\n")

files = {rel: sha_file(os.path.join(ROOT, rel.replace("/", os.sep)))
         for rel in ["inputs/claim.json", "inputs/evidence_1.txt", "inputs/evidence_2.txt"]}
out_hash = sha_file(os.path.join(ROOT, "outputs", "result.txt"))
manifest = {
    "package_id": "DEMO-01-synthetic",
    "note": "合成演示包，用于验证复跑器本身；不含任何真实研究数据",
    "files": files,
    "steps": [
        {"n": 1, "op": "sha256_file", "path": "inputs/claim.json", "expect": files["inputs/claim.json"]},
        {"n": 2, "op": "sha256_file", "path": "inputs/evidence_1.txt", "expect": files["inputs/evidence_1.txt"]},
        {"n": 3, "op": "sha256_file", "path": "inputs/evidence_2.txt", "expect": files["inputs/evidence_2.txt"]},
        {"n": 4, "op": "spine_hash", "paths": ["inputs/evidence_1.txt", "inputs/evidence_2.txt"], "expect": spine},
        {"n": 5, "op": "sha256_file", "path": "outputs/result.txt", "expect": out_hash},
    ],
    "expected": {"outputs/result.txt": out_hash},
}
write("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
print("demo 包已生成：", ROOT)
print("spine:", spine[:32], "…")
