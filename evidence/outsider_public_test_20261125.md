# 匿名公开复跑记录 · 2026-11-25

条件：**不带任何 token、不加 Authorization 头**，只用 `raw.githubusercontent.com` 拉公开仓文件；在空 venv（site-packages 仅 pip 26.3）里重建并实跑。

## 第一次（无重试）

```
GET 200  README.md                 2866 B  sha256=1cdba20136661cce
FAIL     rerun/README.md           ConnectionResetError [WinError 10054]
GET 200  rerun/verify_chain.py     6359 B  sha256=d00a658646f8dbbb
GET 200  rerun/redteam.py          4078 B  sha256=a168a2ac0185bdd2
GET 200  rerun/make_demo_pkg.py    3060 B  sha256=3df911d6ec911b05
GET 200  evidence/demo_run.json    2027 B  sha256=26e151aabeb742d2
FAIL     evidence/outsider_run.json TimeoutError
FAIL     evidence/io_selftest_clean_venv.log  ConnectionResetError
取回 5/8
[校验] 14/14 PASS   [红队] 6/6 拦下
```

三个失败**不是 404**，是国内网络到 raw.githubusercontent 的连接被重置/超时。

## 第二次（加退避重试，1.5s×n）

```
GET 200  README.md                    2866 B  sha256=1cdba20136661cce  重试0次
GET 200  rerun/README.md              2901 B  sha256=20b4ca1c8af9dcd7  重试0次
GET 200  rerun/verify_chain.py        6359 B  sha256=d00a658646f8dbbb  重试0次
GET 200  rerun/redteam.py             4078 B  sha256=a168a2ac0185bdd2  重试1次
GET 200  rerun/make_demo_pkg.py       3060 B  sha256=3df911d6ec911b05  重试1次
GET 200  evidence/demo_run.json       2027 B  sha256=26e151aabeb742d2  重试0次
GET 200  evidence/outsider_run.json   2027 B  sha256=26e151aabeb742d2  重试0次
GET 200  evidence/io_selftest_clean_venv.log 1746 B sha256=ffeff38a269e1247
取回 8/8
[重建 demo 包] spine: 5e60affe1ba88f2c63bba91e81df6015 …
[校验] SUMMARY: 14/14 项通过 → PASS   exit=0
[红队] SUMMARY: 6/6 攻击被拦下；baseline PASS   exit=0
OUTSIDER_PUBLIC_TEST = PASS
```

## 两个可复用的坑

1. **`git clone` 会失败**（`Recv failure: Connection was reset`），但同一台机器上 HTTPS API 与 raw 下载能通。所以外人复跑不要指望 `git clone`，直接走 raw 或 zip。
2. **必须带重试**。不带重试时 8 个文件里 3 个失败；带 1.5s×n 退避后 8/8。若不加重试，会误判成"仓库缺件"——这和本轮账本的病同型：**把网络抖动当成对方的问题**。

## 边界（不改口径）

- 这次"外人"仍然是我，只是去掉了全部凭据。它证明的是"**公网可取、无凭据可复跑**"，不等于"独立第三方已签署"。真正的 E2 仍然空着。
- `evidence/demo_run.json` 与 `outsider_run.json` sha256 相同（`26E151AABEB742D2`），说明两次运行逐字节一致。
