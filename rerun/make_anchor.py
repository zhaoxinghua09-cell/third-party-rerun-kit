# -*- coding: utf-8 -*-
"""make_anchor.py —— 生成信任锚 anchor.json：把公钥钉在公开仓的某个 commit 上

为什么用这个当锚（而不是 DNS well-known）：
  1) 现在没有可挂 /.well-known/ 的域名，DNS 锚只能写不能跑；
  2) git commit 是不可回改的（改历史要 force-push 且 sha 会变），把"公钥首次公开的 commit"
     钉住之后，**换钥匙就会暴露**：新包里的公钥与锚里的指纹不一致 → 直接 FAIL；
  3) 它锚定的是"GitHub 账号 + 某个 commit"，不是一个法定身份。账号被盗或强推都能破。
     所以这一层的准确说法是"**可检测的钥匙替换**"，不是"身份认证"。

用法：python make_anchor.py --commit <sha> [--online]
"""
import sys, os, json, hashlib, base64, argparse, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
OWNER, REPO, PATH = "zhaoxinghua09-cell", "third-party-rerun-kit", "trust/ed25519.pub"

ap = argparse.ArgumentParser()
ap.add_argument("--pkg", default=os.path.join(HERE, "demo_pkg_signed"))
ap.add_argument("--out", default=os.path.join(HERE, "anchor.json"))
a = ap.parse_args()

m = json.load(open(os.path.join(a.pkg, "manifest.json"), encoding="utf-8"))
pub_b64 = m["signature"]["public_key_b64"]
pub_sha = hashlib.sha256(base64.b64decode(pub_b64)).hexdigest()

# 取当前 main 上 trust/ed25519.pub 的 blob sha 与最近提交（作为"首次公开"的锚点）
H = {"User-Agent": "anchor/1.0", "Accept": "application/vnd.github+json"}
c = json.loads(urllib.request.urlopen(urllib.request.Request(
    f"https://api.github.com/repos/{OWNER}/{REPO}/commits?path={PATH}&per_page=1", headers=H), timeout=30).read())
commit = c[0]["sha"] if c else None
blob = json.loads(urllib.request.urlopen(urllib.request.Request(
    f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{PATH}?ref={commit or 'main'}", headers=H), timeout=30).read())

anchor = {
    "type": "github-commit",
    "owner": OWNER, "repo": REPO, "path": PATH,
    "commit": commit, "blob": blob["sha"],
    "key_sha256": pub_sha,
    "key_b64": pub_b64,
    "scope": "锚定'公钥在本仓某次提交中首次公开'；不是身份认证",
    "limits": ["账号被盗可替换", "强推改历史会改变 commit sha，必须重新核对锚"],
}
json.dump(anchor, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("anchor 已写：", a.out)
print("commit:", (commit or "-")[:12], "| blob:", blob["sha"][:12], "| key_sha256:", pub_sha[:16])
