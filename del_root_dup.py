# -*- coding: utf-8 -*-
"""del_root_dup.py —— 删除公开仓根目录误推的 verify_chain.py（保留 rerun/verify_chain.py）"""
import os, json, urllib.request
T = os.environ["GH_TOKEN"]
BASE = "https://api.github.com/repos/zhaoxinghua09-cell/third-party-rerun-kit/contents/"
H = {"Authorization": "Bearer " + T, "Accept": "application/vnd.github+json", "User-Agent": "cleanup/1.0"}
p = "verify_chain.py"
cur = json.loads(urllib.request.urlopen(urllib.request.Request(BASE + p, headers=H)).read())
req = urllib.request.Request(BASE + p, method="DELETE", headers=H,
    data=json.dumps({"message": "remove stray duplicate at repo root", "sha": cur["sha"], "branch": "main"}).encode())
print("DELETE ->", urllib.request.urlopen(req).status)
