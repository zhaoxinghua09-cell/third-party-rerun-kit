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

def a7(pkg):
    # 声明了签名，但文件不存在
    m = json.load(open(os.path.join(pkg, "manifest.json"), encoding="utf-8"))
    m["signature"] = {"type": "sigstore-bundle", "path": "attest/none.sigstore.json"}
    json.dump(m, open(os.path.join(pkg, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def a8(pkg):
    # 签名文件存在、哈希自洽、且已在 files/steps 里登记；本机无 cosign → 必须 INCOMPLETE(exit 4)，绝不能 PASS
    os.makedirs(os.path.join(pkg, "attest"), exist_ok=True)
    sp = os.path.join(pkg, "attest/fake.sigstore.json")
    open(sp, "w", encoding="utf-8").write('{"fake":"bundle"}\n')
    m = json.load(open(os.path.join(pkg, "manifest.json"), encoding="utf-8"))
    m["files"]["attest/fake.sigstore.json"] = sha_file(sp)
    m["steps"].append({"n": 7, "op": "sha256_file", "path": "attest/fake.sigstore.json",
                       "expect": sha_file(sp)})
    m["signature"] = {"type": "sigstore-bundle", "path": "attest/fake.sigstore.json",
                      "sha256": sha_file(sp), "artifact": "outputs/result.txt"}
    json.dump(m, open(os.path.join(pkg, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def a9(pkg):
    # 签名不动、把公布的公钥换成另一把 → 验签必须失败
    import base64
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    os.makedirs(os.path.join(pkg, "attest"), exist_ok=True)
    art = os.path.join(pkg, "outputs/result.txt")
    real = Ed25519PrivateKey.generate()
    other = Ed25519PrivateKey.generate()
    sig = real.sign(open(art, "rb").read())
    other_pub = base64.b64encode(other.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)).decode()
    sp = os.path.join(pkg, "attest/swapped.sig.json")
    json.dump({"alg": "ed25519", "target": "outputs/result.txt", "target_sha256": sha_file(art),
               "public_key_b64": other_pub, "sig_b64": base64.b64encode(sig).decode()},
              open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    m = json.load(open(os.path.join(pkg, "manifest.json"), encoding="utf-8"))
    m["files"]["attest/swapped.sig.json"] = sha_file(sp)
    m["steps"].append({"n": 9, "op": "sha256_file", "path": "attest/swapped.sig.json", "expect": sha_file(sp)})
    m["signature"] = {"type": "ed25519", "path": "attest/swapped.sig.json",
                      "sha256": sha_file(sp), "artifact": "outputs/result.txt", "public_key_b64": other_pub}
    json.dump(m, open(os.path.join(pkg, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def a10(pkg):
    # 换钥但保留锚：签名自洽（用攻击者私钥签的），锚仍指向原公钥 → 必须被锚抓出
    import base64
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    os.makedirs(os.path.join(pkg, "attest"), exist_ok=True)
    art = os.path.join(pkg, "outputs/result.txt")
    evil = Ed25519PrivateKey.generate()
    sig = evil.sign(open(art, "rb").read())
    evil_pub = base64.b64encode(evil.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)).decode()
    sp = os.path.join(pkg, "attest/new.sig.json")
    json.dump({"alg": "ed25519", "target": "outputs/result.txt", "target_sha256": sha_file(art),
               "public_key_b64": evil_pub, "sig_b64": base64.b64encode(sig).decode()},
              open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 锚沿用"正确"的那把（模拟攻击者不敢改锚，只换钥）
    anc = os.path.join(pkg, "attest/anchor.json")
    os.makedirs(os.path.dirname(anc), exist_ok=True)
    json.dump({"type": "github-commit", "owner": "zhaoxinghua09-cell", "repo": "third-party-rerun-kit",
               "path": "trust/ed25519.pub", "commit": "deadbeef", "blob": "deadbeef",
               "key_sha256": "0" * 64, "key_b64": "x"}, open(anc, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    m = json.load(open(os.path.join(pkg, "manifest.json"), encoding="utf-8"))
    for rel, p in [("attest/new.sig.json", sp), ("attest/anchor.json", anc)]:
        m["files"][rel] = sha_file(p)
        m["steps"].append({"n": len(m["steps"]) + 1, "op": "sha256_file", "path": rel, "expect": m["files"][rel]})
    m["signature"] = {"type": "ed25519", "path": "attest/new.sig.json", "sha256": sha_file(sp),
                      "artifact": "outputs/result.txt", "public_key_b64": evil_pub,
                      "anchor": "attest/anchor.json"}
    json.dump(m, open(os.path.join(pkg, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def main():
    print("baseline（未篡改）应先 PASS：")
    code, out = run(DEMO)
    ok_base = code == 0
    print(f"  [{'PASS' if ok_base else 'FAIL'}] exit={code}")
    if not ok_base:
        print(out[-400:])
        return 2
    print("\n八种攻击（都必须被拦下，或判 INCOMPLETE 而不得 PASS）：")
    caught = [
        attack("A1 改证据一个字节", a1),
        attack("A2 篡改期望输出", a2),
        attack("A3 夹带未声明文件", a3),
        attack("A4 自证循环（改文件+改期望）", a4),
        attack("A5 截断哈希到 8 位", a5),
        attack("A6 抽走链式步骤", a6),
        attack("A7 声明签名但文件缺失", a7),
        attack("A8 签名自洽但无法验证（cosign 缺）", a8),
        attack("A9 签名不动、公钥被换", a9),
        attack("A10 换私钥重签、锚不改（锚应抓出）", a10),
    ]
    n = sum(caught)
    print(f"\nSUMMARY: {n}/{len(caught)} 攻击被拦下；baseline {'PASS' if ok_base else 'FAIL'}")
    return 0 if (ok_base and n == len(caught)) else 3

if __name__ == "__main__":
    sys.exit(main())
