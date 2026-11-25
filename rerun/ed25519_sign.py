# -*- coding: utf-8 -*-
"""ed25519_sign.py —— 用 Ed25519 真签包内产物，生成 demo_pkg_signed/

为什么要签名这一层：我们原来的复跑器只证明"声明与文件一致"，任何人都能造一份自洽的包。
签名把"这是谁做的"变成一个可验证的问题——但注意，**公钥随包发布只解决"同一把钥匙签的"，
解决不了"这把钥匙是谁"**；真正的身份绑定要靠外部信任锚（DNS/组织目录/透明日志）。
这句话必须跟签名一起说，否则签名会变成装饰。

密钥：D:\\Workbuddy\\20261125-国际组织信息收取\\keys\\ed25519_private.pem（不入库、不公开）
"""
import sys, os, json, shutil, hashlib, base64
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

HERE = os.path.dirname(os.path.abspath(__file__))
KEYS = r"D:\Workbuddy\20261125-国际组织信息收取\keys"
SRC = os.path.join(HERE, "demo_pkg")
DST = os.path.join(HERE, "demo_pkg_signed")

def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()

os.makedirs(KEYS, exist_ok=True)
priv_path = os.path.join(KEYS, "ed25519_private.pem")
if os.path.exists(priv_path):
    priv = serialization.load_pem_private_key(open(priv_path, "rb").read(), password=None)
else:
    priv = Ed25519PrivateKey.generate()
    open(priv_path, "wb").write(priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()))
pub = priv.public_key()
pub_b64 = base64.b64encode(pub.public_bytes(
    encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)).decode()
print("公钥(原始64字节, base64):", pub_b64)

if os.path.exists(DST):
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)

art_rel = "outputs/result.txt"
art = os.path.join(DST, art_rel.replace("/", os.sep))
sig = priv.sign(open(art, "rb").read())
sig_rel = "attest/result.sig.json"
sig_path = os.path.join(DST, sig_rel.replace("/", os.sep))
os.makedirs(os.path.dirname(sig_path), exist_ok=True)
payload = {"alg": "ed25519", "target": art_rel, "target_sha256": sha_file(art),
           "public_key_b64": pub_b64, "sig_b64": base64.b64encode(sig).decode(),
           "note": "签名只证明'这把私钥签过这份字节'；钥匙归属需外部信任锚"}
json.dump(payload, open(sig_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("已签名:", art_rel, "->", sig_rel)

# 独立验签（先自证能验）
Ed25519PublicKey.from_public_bytes(base64.b64decode(pub_b64)).verify(sig, open(art, "rb").read())
print("自验签: OK")

m = json.load(open(os.path.join(DST, "manifest.json"), encoding="utf-8"))
m["files"][sig_rel] = sha_file(sig_path)
m["steps"].append({"n": len(m["steps"]) + 1, "op": "sha256_file", "path": sig_rel, "expect": m["files"][sig_rel]})
m["signature"] = {"type": "ed25519", "path": sig_rel, "sha256": m["files"][sig_rel],
                  "artifact": art_rel, "public_key_b64": pub_b64}
json.dump(m, open(os.path.join(DST, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

import subprocess
r = subprocess.run([sys.executable, os.path.join(HERE, "verify_chain.py"), "--pkg", DST,
                    "--json", os.path.join(HERE, "signed_run.json")], capture_output=True, text=True, encoding="utf-8", errors="replace")
print("\nverify_chain exit=", r.returncode)
for l in r.stdout.splitlines():
    if l.startswith(("[PASS]", "[FAIL]", "[INCOMPLETE]", "SUMMARY")):
        print(l)
sys.exit(0 if r.returncode == 0 else 3)
