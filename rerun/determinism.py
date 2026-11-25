# -*- coding: utf-8 -*-
"""determinism.py —— 重复运行一致度分级（借 arXiv 2611.09214 的 determinism tier 思路）

做什么：把包复制两份到全新临时目录，各跑一次 manifest 声明的 producer，比对两份产物。

分级（我们自己定义，写明判据，不假装是标准）：
  byte-identical  全部产物逐字节相同
  near-identical  只有声明在 "volatile" 列表里的文件不同（如时间戳行），其余逐字节相同
  unstable        其他情况

为什么必须跑两次以上：一次成功是运气。作者自己跑两次一致才叫可为他人复跑的下限。
注意：这会执行 producer（对方代码）。所以默认只在你已经读过 producer、且愿意承担时才加 --execute。
"""
import sys, os, json, shutil, subprocess, tempfile, hashlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()

def tree_hashes(root, sub="outputs"):
    d = os.path.join(root, sub)
    out = {}
    for dirpath, _, files in os.walk(d):
        for f in files:
            p = os.path.join(dirpath, f)
            out[os.path.relpath(p, d).replace("\\", "/")] = sha_file(p)
    return out

def run_once(pkg, producer, tmp):
    dst = os.path.join(tmp, "run")
    shutil.copytree(pkg, dst)
    r = subprocess.run([sys.executable, os.path.join(dst, producer), dst],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return dst, r

def main(argv):
    pkg = argv[1] if len(argv) > 1 else "demo_pkg"
    if "--execute" not in argv:
        print("拒绝执行对方代码：请先读 producer，再加 --execute"); return 2
    pkg = os.path.abspath(pkg)
    m = json.load(open(os.path.join(pkg, "manifest.json"), encoding="utf-8"))
    producer = m.get("producer")
    if not producer:
        print("manifest 未声明 producer，无法做确定性分级"); return 2
    volatile = set(m.get("volatile") or [])

    results = []
    for i in range(2):
        tmp = tempfile.mkdtemp(prefix=f"det{i}_")
        dst, r = run_once(pkg, producer, tmp)
        results.append(tree_hashes(dst))
        print(f"  run{i+1}: exit={r.returncode} files={len(results[-1])}")
        shutil.rmtree(tmp, ignore_errors=True)

    a, b = results
    if set(a) != set(b):
        tier, diff = "unstable", sorted(set(a) ^ set(b))
    else:
        diff = [k for k in a if a[k] != b[k]]
        if not diff:
            tier = "byte-identical"
        elif set(diff) <= volatile:
            tier = "near-identical"
        else:
            tier = "unstable"
    print(f"\n差异文件 {len(diff)} 个" + (f"：{diff[:6]}" if diff else ""))
    print(f"DETERMINISM_TIER={tier}")
    out = {"pkg": pkg, "producer": producer, "tier": tier, "diff": diff,
           "runs": [{k: v[:16] for k, v in r.items()} for r in results]}
    name = "determinism_result.json"
    if "--out" in argv:
        name = argv[argv.index("--out") + 1]
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("saved", p)
    return 0 if tier in ("byte-identical", "near-identical") else 3

if __name__ == "__main__":
    sys.exit(main(sys.argv))
