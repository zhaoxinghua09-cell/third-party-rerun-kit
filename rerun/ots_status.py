# -*- coding: utf-8 -*-
"""ots_status.py —— 读 .ots 证明，报告"锚到了哪一层"（不改口：pending ≠ 上链）

用法：python ots_status.py <file>.ots
判读：
  - 出现 BitcoinBlockHeaderAttestation → 已上链，任何人可独立验（需区块头）
  - 只有 PendingAttestation       → 已提交到日历（Merkle 树里），**尚未上链**，不能当"已锚定"
"""
import sys, os, re, subprocess

OTS = r"D:\Workbuddy\tools\otsvenv\Scripts\ots.exe"

def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    p = argv[1]
    if not os.path.exists(p):
        print("文件不存在:", p); return 2
    r = subprocess.run([OTS, "info", p], capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    cal = re.findall(r"PendingAttestation\('([^']+)'\)", out)
    btc = re.findall(r"BitcoinBlockHeaderAttestation\((\d+)\)", out)
    print(f"文件: {p}  ({os.path.getsize(p)} B)")
    print(f"日历 attestation: {len(cal)} 个" + (f" {cal}" if cal else ""))
    print(f"比特币区块 attestation: {len(btc)} 个" + (f" 高度={btc}" if btc else ""))
    status = "BITCOIN_CONFIRMED" if btc else ("PENDING_CALENDAR" if cal else "UNKNOWN")
    print("OTS_STATUS =", status)
    if status == "PENDING_CALENDAR":
        print("说明：已提交日历，尚未进区块。此时只能说'我们提交过'，不能说'已锚定'。上链后用 ots upgrade 再验。")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
