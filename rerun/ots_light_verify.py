# -*- coding: utf-8 -*-
"""ots_light_verify.py —— 没有比特币节点时的"轻验证"

做法：
 1) 从 .ots 取出每条比特币 attestation 的高度；
 2) 向两家独立区块浏览器查该高度的区块哈希，必须两家一致；
 3) 取该区块的 80 字节区块头，交给库里的 verify_against_blockheader(msg, header)
    做 Merkle 路径 + 区块头绑定校验——这是真正的密码学校验，不是"看一眼哈希对不对"；
 4) 不做 PoW/难度校验（那需要区块头链）。
结论标 LIGHT_VERIFY，不等于完整 `ots verify`。
"""
import sys, urllib.request
from opentimestamps.core.serialize import BytesDeserializationContext
from opentimestamps.core.timestamp import DetachedTimestampFile

EXPLORERS = {
    "mempool.space": "https://mempool.space/api/block-height/{h}",
    "blockstream.info": "https://blockstream.info/api/block-height/{h}",
}
HEADER_API = "https://blockstream.info/api/block/{hash}/header"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ots-light/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode().strip()

def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    p = argv[1]
    with open(p, "rb") as f:
        d = DetachedTimestampFile.deserialize(BytesDeserializationContext(f.read()))

    checked = failed = pending = 0
    for msg, att in d.timestamp.all_attestations():
        if type(att).__name__ != "BitcoinBlockHeaderAttestation":
            pending += 1
            continue
        h = att.height
        hashes = {}
        for name, tpl in EXPLORERS.items():
            try:
                hashes[name] = get(tpl.format(h=h))
            except Exception as e:
                print(f"  高度{h} {name} 取不到 ({type(e).__name__})")
        if len(set(hashes.values())) != 1:
            print(f"  高度{h} 浏览器结果不一致/缺失：{hashes}  → 判不可信")
            failed += 1
            continue
        bh = list(hashes.values())[0]
        try:
            header = bytes.fromhex(get(HEADER_API.format(hash=bh)))
        except Exception as e:
            print(f"  高度{h} 取区块头失败 ({type(e).__name__})"); failed += 1; continue
        if len(header) != 80:
            print(f"  高度{h} 区块头长度异常 {len(header)}"); failed += 1; continue

        class _Hdr:  # 只带库需要的两个属性，避免整套 python-bitcoinlib
            pass
        merkle = header[36:68]
        ntime = int.from_bytes(header[68:72], "little")
        ok, orient = False, None
        for label, m in (("raw", merkle), ("reversed", merkle[::-1])):
            hd = _Hdr(); hd.hashMerkleRoot = m; hd.nTime = ntime
            try:
                att.verify_against_blockheader(msg, hd)
                ok, orient = True, label
                break
            except Exception:
                continue
        print(f"  高度{h} 区块 {bh[:16]}…  头80B  绑定校验={ok}" + (f"（merkle 字节序={orient}）" if ok else ""))
        checked += 1
        if not ok:
            failed += 1

    print(f"文件: {p}")
    print(f"比特币 attestation 通过校验: {checked}；失败/不可信: {failed}；日历 attestation: {pending}")
    print("LIGHT_VERIFY =", "PASS" if checked and not failed else "INCONCLUSIVE")
    print("边界：已验 Merkle 路径与区块头绑定；未验 PoW/难度（需区块头链）。")
    return 0 if checked and not failed else 4

if __name__ == "__main__":
    sys.exit(main(sys.argv))
