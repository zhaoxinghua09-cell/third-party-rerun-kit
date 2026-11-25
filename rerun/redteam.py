# -*- coding: utf-8 -*-
"""redteam.py —— 对复跑器本身的红队：6 种攻击，全部必须被判 FAIL（否则复跑器不合格）

攻击清单：
  A1 改一个证据字节（哈希应立刻不匹配）
  A2 篡改 expected/result.txt（期望输出被动过）
  A3 夹带未声明文件（package 里多塞一个 payload.txt）
  A4 换掉 manifest 里的某个 expect 为攻击者自算值（并同步改文件）——"自证循环"
  A5 只给短哈希前缀（把 expect 截断成 8 位，碰撞空间被压到可暴力）
  A6 删掉 manifest 的 steps（只剩文件哈希，链式校验被抽走）

判据：每种攻击下 verify_chain.py 必须非 0 退出；否则该攻击"逃逸"，红队判失败。
"""
import sys, os, json, shutil, hashlib, subprocess, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
VERIFY = os.path.join(HERE, "verify_chain.py")
DEMO = os.path.join(HERE, "demo_pkg")

def run(pkg):
    r = subprocess.run([sys.executable, VERIFY, "--pkg", pkg], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout

def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()

def attack(name, mutate, expect_code=3):
    work = tempfile.mkdtemp(prefix="rt_")
    dst = os.path.join(work, "pkg")
    shutil.copytree(DEMO, dst)
    mutate(dst)
    code, out = run(dst)
    tail = [l for l in out.splitlines() if l.strip().startswith(("[FAIL]", "SUMMARY"))]
    caught = code != 0
    print(f"  [{'拦下' if caught else '逃逸!'}] {name} → exit={code}")
    for l in tail[:2]:
        print("        ", l.strip()[:150])
    shutil.rmtree(work, ignore_errors=True)
    return caught

def a1(pkg):
    p = os.path.join(pkg, "inputs/evidence_1.txt")
    open(p, "a", encoding="utf-8").write("tampered\n")

def a2(pkg):
    p = os.path.join(pkg, "outputs/result.txt")
    open(p, "w", encoding="utf-8").write("spine_sha256=deadbeef\n")

def a3(pkg):
    open(os.path.join(pkg, "payload.txt"), "w", encoding="utf-8").write("smuggled\n")

def a4(pkg):
    # 攻击者改文件 + 同步改 manifest 期望值（试图让"自证"通过）
    p = os.path.join(pkg, "inputs/evidence_2.txt")
    open(p, "w", encoding="utf-8").write("batch B\nforged record\n")
    m = json.load(open(os.path.join(pkg, "manifest.json"), encoding="utf-8"))
    m["files"]["inputs/evidence_2.txt"] = sha_file(p)
    m["steps"][1]["expect"] = sha_file(p)
    # 但 spine 与 expected 仍是原值，复跑器应发现不一致
    json.dump(m, open(os.path.join(pkg, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def a5(pkg):
    m = json.load(open(os.path.join(pkg, "manifest.json"), encoding="utf-8"))
    m["steps"][2]["expect"] = m["steps"][2]["expect"][:8]
    json.dump(m, open(os.path.join(pkg, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def a6(pkg):
    m = json.load(open(os.path.join(pkg, "manifest.json"), encoding="utf-8"))
    m["steps"] = []
    json.dump(m, open(os.path.join(pkg, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def main():
    print("baseline（未篡改）应先 PASS：")
    code, out = run(DEMO)
    ok_base = code == 0
    print(f"  [{'PASS' if ok_base else 'FAIL'}] exit={code}")
    if not ok_base:
        print(out[-400:])
        return 2
    print("\n六种攻击（都必须被拦下）：")
    caught = [
        attack("A1 改证据一个字节", a1),
        attack("A2 篡改期望输出", a2),
        attack("A3 夹带未声明文件", a3),
        attack("A4 自证循环（改文件+改期望）", a4),
        attack("A5 截断哈希到 8 位", a5),
        attack("A6 抽走链式步骤", a6),
    ]
    n = sum(caught)
    print(f"\nSUMMARY: {n}/6 攻击被拦下；baseline {'PASS' if ok_base else 'FAIL'}")
    return 0 if (ok_base and n == 6) else 3

if __name__ == "__main__":
    sys.exit(main())
