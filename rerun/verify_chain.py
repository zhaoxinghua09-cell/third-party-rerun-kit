# -*- coding: utf-8 -*-
"""verify_chain.py —— 第三方验证链复跑器（只做声明式校验，不执行对方代码）

设计原则（为什么这么做）：
  1) 不执行对方脚本：拿到陌生代码就跑，等于把机器交出去。默认只做"声明式校验"——
     重算文件哈希、重算链式哈希、核对期望输出。对方若要求跑脚本，需显式 --run-steps，
     且只跑 manifest 里声明的命令，逐条打印，不吞输出。
  2) 白名单：包里出现 manifest 未声明的文件 → 直接判 FAIL（防夹带）。
  3) 每条判定都要可复算：打印 algo、输入文件、期望、实算，四列齐全。

manifest.json 结构：
{
  "package_id": "...",
  "files": {"inputs/a.txt": "<sha256>", ...},
  "steps": [
     {"n":1, "op":"sha256_file", "path":"inputs/a.txt", "expect":"<sha256>"},
     {"n":2, "op":"spine_hash",  "paths":["inputs/a.txt","inputs/b.txt"], "expect":"<sha256>"}
  ],
  "expected": {"outputs/result.txt": "<sha256>"}
}

退出码：0 全过；3 任一不过；2 manifest 缺失/格式错。
"""
import sys, os, json, hashlib, argparse, urllib.request

def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()

def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--json", default=None)
    ap.add_argument("--online", action="store_true", help="联机核对锚（需网络；取不到判 INCOMPLETE）")
    a = ap.parse_args()
    root = os.path.abspath(a.pkg)
    mpath = os.path.join(root, "manifest.json")
    if not os.path.exists(mpath):
        print("FAIL: manifest.json 不存在"); return 2
    try:
        m = json.load(open(mpath, encoding="utf-8"))
    except Exception as ex:
        print("FAIL: manifest 解析失败", type(ex).__name__); return 2

    results, ok = [], True
    def add(name, passed, detail):
        nonlocal ok
        results.append({"check": name, "pass": bool(passed), "detail": detail})
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {name} — {detail}")

    print(f"包：{root}\npackage_id：{m.get('package_id','(缺)')}\n")

    # 0) 结构门槛：链为空 / 有未覆盖的声明 → 不得判 PASS（"声明数=实际数"铁律）
    steps = m.get("steps") or []
    add("structure（steps 非空）", len(steps) > 0, f"steps={len(steps)}")
    covered = set()
    for st in steps:
        if st.get("op") == "sha256_file":
            covered.add(st.get("path"))
        elif st.get("op") == "spine_hash":
            covered.update(st.get("paths") or [])
    declared_files = set(m.get("files", {}))
    orphans = sorted(declared_files - covered)
    add("coverage（每个声明文件都被链引用）", not orphans, f"未覆盖 {len(orphans)} 个" + (f"：{orphans[:5]}" if orphans else ""))
    outs = set(m.get("expected", {}))
    out_unbound = sorted(outs - covered)
    add("coverage（每个期望输出都被链绑定）", not out_unbound, f"未绑定 {len(out_unbound)} 个" + (f"：{out_unbound}" if out_unbound else ""))
    # 全哈希：expect 必须 64 位 hex，短前缀一律拒（否则碰撞空间可暴力）
    bad_len = []
    for st in steps:
        e = (st.get("expect") or "")
        if len(e) != 64 or any(c not in "0123456789abcdefABCDEF" for c in e):
            bad_len.append(st.get("n"))
    for rel, e in (m.get("expected") or {}).items():
        if len(e) != 64 or any(c not in "0123456789abcdefABCDEF" for c in e):
            bad_len.append(rel)
    add("hash-length（全部 expect 为 64 位 sha256）", not bad_len, f"不合规 {bad_len[:5]}")

    # 1) 白名单：未声明文件即夹带
    declared = set(m.get("files", {})) | set(m.get("expected", {})) | {"manifest.json"}
    on_disk = set()
    for dirpath, _, files in os.walk(root):
        for f in files:
            rel = os.path.relpath(os.path.join(dirpath, f), root).replace("\\", "/")
            on_disk.add(rel)
    extra = sorted(on_disk - declared)
    add("white-list（无夹带）", not extra, f"未声明文件 {len(extra)} 个" + (f"：{extra[:5]}" if extra else ""))

    # 2) 逐文件哈希
    for rel, exp in m.get("files", {}).items():
        p = os.path.join(root, rel.replace("/", os.sep))
        if not os.path.exists(p):
            add(f"file {rel}", False, "文件缺失"); continue
        got = sha_file(p)
        add(f"file {rel}", got == exp.lower(), f"expect {exp[:16]} / got {got[:16]}")

    # 3) 链步骤
    for st in m.get("steps", []):
        n, op = st.get("n"), st.get("op")
        if op == "sha256_file":
            p = os.path.join(root, st["path"].replace("/", os.sep))
            got = sha_file(p) if os.path.exists(p) else ""
            add(f"step{n} sha256_file({st['path']})", got == st["expect"].lower(), f"expect {st['expect'][:16]} / got {got[:16]}")
        elif op == "spine_hash":
            h = hashlib.sha256()
            missing = []
            for rel in st["paths"]:
                p = os.path.join(root, rel.replace("/", os.sep))
                if not os.path.exists(p):
                    missing.append(rel); continue
                h.update(open(p, "rb").read())
            got = h.hexdigest() if not missing else ""
            add(f"step{n} spine_hash({len(st['paths'])} 文件)", got == st["expect"].lower(),
                f"expect {st['expect'][:16]} / got {(got or '-')[:16]}" + (f" 缺 {missing}" if missing else ""))
        else:
            add(f"step{n} {op}", False, "未知 op，拒绝猜测")

    # 4) 期望输出
    for rel, exp in m.get("expected", {}).items():
        p = os.path.join(root, rel.replace("/", os.sep))
        got = sha_file(p) if os.path.exists(p) else ""
        add(f"expected {rel}", got == exp.lower(), f"expect {exp[:16]} / got {(got or '-')[:16]}")

    # 5) 签名（真实性层）：声明了签名就必须真能验，否则整体判 INCOMPLETE，绝不当 PASS
    incomplete = False
    sig = m.get("signature")
    if not sig:
        print("  [INFO] UNSIGNED — 本包只声明完整性，不含身份/真实性（这是允许的，但对外只能讲复现性）")
    else:
        sp = os.path.join(root, (sig.get("path") or "").replace("/", os.sep))
        if not sig.get("path") or not os.path.exists(sp):
            add("signature（声明文件存在）", False, f"声明 {sig.get('path')} 但文件不在")
        elif (sig.get("type") or "") == "ed25519":
            # 自包含 Ed25519：目标字节的哈希 + 用包内公钥验签
            try:
                import base64, json as _json
                from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
                payload = _json.load(open(sp, encoding="utf-8"))
                art = os.path.join(root, (sig.get("artifact") or payload.get("target") or "").replace("/", os.sep))
                if not os.path.exists(art):
                    add("signature（被签产物存在）", False, f"产物 {sig.get('artifact')} 不在包内")
                    incomplete = True
                else:
                    actual = sha_file(art)
                    add("signature（被签字节未被改动）", actual == payload.get("target_sha256", "").lower(),
                        f"声明 {str(payload.get('target_sha256'))[:16]} / 实算 {actual[:16]}")
                    pub_b64 = sig.get("public_key_b64") or payload.get("public_key_b64")
                    Ed25519PublicKey.from_public_bytes(base64.b64decode(pub_b64)).verify(
                        base64.b64decode(payload["sig_b64"]), open(art, "rb").read())
                    add("signature（Ed25519 验签）", True, "验签通过（只证明此钥匙签过，不证明钥匙归属）")

                    # 信任锚：把公钥钉在公开仓的某次提交上，用于"检测换钥"
                    anc_rel = sig.get("anchor")
                    if anc_rel:
                        ap = os.path.join(root, anc_rel.replace("/", os.sep))
                        if not os.path.exists(ap):
                            add("anchor（锚文件存在）", False, f"声明 {anc_rel} 但文件不在")
                        else:
                            anc = _json.load(open(ap, encoding="utf-8"))
                            got = hashlib.sha256(base64.b64decode(pub_b64)).hexdigest()
                            add("anchor（公钥与锚一致）", got == (anc.get("key_sha256") or "").lower(),
                                f"锚 {str(anc.get('key_sha256'))[:16]} / 包内 {got[:16]}（不一致=疑似换钥）")
                            if a.online:
                                try:
                                    url = (f"https://api.github.com/repos/{anc['owner']}/{anc['repo']}"
                                           f"/contents/{anc['path']}?ref={anc['commit']}")
                                    req = urllib.request.Request(url, headers={
                                        "User-Agent": "verify-chain/1.0", "Accept": "application/vnd.github.raw"})
                                    with urllib.request.urlopen(req, timeout=25) as rr:
                                        remote = rr.read().decode("utf-8", "replace").strip()
                                    add("anchor（联机核对公开仓）", remote == pub_b64,
                                        "远端公钥与包内一致" if remote == pub_b64 else "远端与包内不一致")
                                except Exception as ex:
                                    results.append({"check": "anchor（联机核对公开仓）", "pass": False,
                                                    "detail": f"取不到锚（{type(ex).__name__}）→ UNVERIFIABLE"})
                                    print(f"  [INCOMPLETE] anchor（联机核对公开仓） — 取不到锚（{type(ex).__name__}）")
                                    incomplete = True
                            else:
                                print("  [INFO] anchor 仅做包内一致性核对；加 --online 可联机核对公开仓")
            except ImportError:
                results.append({"check": "signature（Ed25519 验签）", "pass": False,
                                "detail": "cryptography 未安装 → UNVERIFIABLE（不得据此判 PASS）"})
                print("  [INCOMPLETE] signature（Ed25519 验签） — 缺 cryptography，验不了（不得据此判 PASS）")
                incomplete = True
            except Exception as ex:
                add("signature（Ed25519 验签）", False, f"验签失败：{type(ex).__name__}")
        else:
            if sig.get("sha256"):
                add("signature（bundle 哈希）", sha_file(sp) == sig["sha256"].lower(), "bundle sha256 与声明一致")
            import shutil, subprocess
            cosign = shutil.which("cosign")
            if not cosign:
                # "验不了"≠"包错了"：不判 FAIL，判 INCOMPLETE（不污染包本身的对错，但绝不当 PASS）
                results.append({"check": "signature（可验证）", "pass": False,
                                "detail": "cosign 未安装 → UNVERIFIABLE（不得据此判 PASS）"})
                print("  [INCOMPLETE] signature（可验证） — cosign 未安装 → UNVERIFIABLE（不得据此判 PASS）")
                incomplete = True
            else:
                cmd = [cosign, "verify-blob", "--bundle", sp]
                if sig.get("certificate_identity"):
                    cmd += ["--certificate-identity", sig["certificate_identity"]]
                if sig.get("certificate_oidc_issuer"):
                    cmd += ["--certificate-oidc-issuer", sig["certificate_oidc_issuer"]]
                art = os.path.join(root, (sig.get("artifact") or "").replace("/", os.sep))
                if os.path.exists(art):
                    cmd.append(art)
                r = subprocess.run(cmd, capture_output=True, text=True)
                add("signature（cosign verify-blob）", r.returncode == 0,
                    (r.stdout or r.stderr or "").strip().splitlines()[-1][:120] if (r.stdout or r.stderr) else "no output")

    summary = {"pkg": root, "package_id": m.get("package_id"), "pass": ok and not incomplete,
               "signed": bool(sig), "incomplete": incomplete, "checks": results,
               "passed": sum(1 for r in results if r["pass"]), "total": len(results)}
    verdict = "PASS" if (ok and not incomplete) else ("INCOMPLETE" if ok else "FAIL")
    print(f"\nSUMMARY: {summary['passed']}/{summary['total']} 项通过 → {verdict}")
    if a.json:
        json.dump(summary, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("saved", a.json)
    return 0 if verdict == "PASS" else (4 if verdict == "INCOMPLETE" else 3)

if __name__ == "__main__":
    sys.exit(main())
