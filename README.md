# third-party-rerun-kit

一份用来回答这个问题的工具：**"我怎么在不信任对方的前提下，复跑他的一条验证链？"**

适用于论文 / 审计报告 / 证书包自己说"目前只有我们自己跑过"的场合——你被请去做第二个独立方。

## 核心决定：不执行对方代码

拿到陌生代码就在自己机器上跑，等于把机器交出去。

所以 `rerun/verify_chain.py` 默认只做**声明式校验**：

- 对方在 `manifest.json` 里声明"这些文件的 sha256 是这些、这条链的期望值是这些"；
- 你只重算、只比对，不 import、不执行任何他的东西；
- 要跑他的脚本必须显式 `--run-steps`，而且逐条打印命令行。

## 它查什么（20 项门，分三层）

| 门 | 规则 | 防什么 |
|---|---|---|
| structure | `steps` 不能为空 | 链被抽空了还判 PASS（红队第一轮抓到的真漏洞） |
| coverage | 声明的每个文件必须被某条 step 引用 | 声明 12 个、实际只校验 3 个 |
| coverage | 每个期望输出必须被链绑定 | 结论与证据脱钩 |
| hash-length | 期望值必须 64 位 sha256 | 8 位前缀可暴力碰撞 |
| white-list | 包内未声明文件即 FAIL | 夹带 |
| 其余 | 逐文件哈希、逐条链步骤、期望输出 | — |
| signature | 声明了签名就必须真验过；**验不了判 INCOMPLETE，不是 PASS** | 把"有签名文件"当"验签通过" |
| anchor | 若带 `attest/anchor.json`，`--online` 会核对公钥指纹与锚一致 | 换钥后仍拿旧锚充数 |

退出码：0 PASS / 2 参数或 manifest 问题 / 3 FAIL / **4 INCOMPLETE（验不了，不等于通过）**。

另外两层：`determinism.py` 给重复运行一致性分级（byte-identical / near-identical / unstable）；`make_demo_pkg.py` 的 outputs 由 `producer.py` **真跑**生成，不是塞一个结果文件进去。

## 快速跑

```bash
python rerun/make_demo_pkg.py
python rerun/verify_chain.py --pkg rerun/demo_pkg --json my_run.json
python rerun/verify_chain.py --pkg rerun/demo_pkg_signed --online   # 带签名与锚
python rerun/redteam.py
python rerun/determinism.py rerun/demo_pkg --execute
```

对方包到手后：`python rerun/verify_chain.py --pkg <他的包>`（manifest 格式见脚本顶部注释）

## 已实测结果（2026-11-25 / 26）

- 基线包：**16/16 PASS**，exit 0
- 签名包：**23/23 PASS**（离线）、**24/24 PASS**（`--online` 联机核对锚）
- 红队：**A1–A10 十攻 10/10 拦下**（第一版 5/6，A6 逃逸过——抽走 steps 仍 PASS；历史见 `rerun/README.md`）
- 确定性：稳定包 byte-identical，写入时间戳的对照包 unstable（`evidence/determinism_*.json`）
- 空 venv（只有 pip、无密钥、不联网）：**20/21，判 INCOMPLETE / exit 4**——同一包在不同环境给出不同但各自正确的判定，这是设计不是 bug
- 匿名从本仓取件重跑：11/11 取回、16/16 通过、8/8 拦下（`evidence/outsider_public_test_20261125.md`）

## 信任锚：两层，都是外部可查的

**L1 账号锚**：`trust/anchor.json` 钉住"公钥在哪个 commit 首次公开"（owner/repo/path/commit/blob/key_sha256）。换钥会被发现——A10 实测：换私钥重签而锚不改 → 锚指纹不一致，exit 3。

**L2 时间锚（OpenTimestamps → 比特币）**：`trust/ed25519.pub.ots` 与 `trust/key-statement.json.ots` 已于 **2026-11-26** 完成升级，绑定到比特币区块 **977531 / 977532**。

自己验（任选其一）：

```bash
pip install opentimestamps-client
ots verify trust/ed25519.pub.ots        # 完整验证，需要比特币区块头链（本机 node 或 SPV）
```

没有比特币节点时，用本仓的轻验证（会向两家独立浏览器取区块头，做 Merkle 路径 + 区块头绑定校验）：

```bash
pip install opentimestamps-client
python rerun/ots_light_verify.py trust/ed25519.pub.ots
# → 高度 977531/977532  绑定校验=True   LIGHT_VERIFY = PASS
```

`LIGHT_VERIFY` 的边界写清楚：**验了 Merkle 路径与区块头绑定，没验 PoW/难度**。所以它不是"完整验证通过"的同义词。

实测中还留了一个真实细节：升级当天 `btc.calendar.catallaxy.com` 回了 `Not found`，是 alice/bob 两家给出的 attestation——多日历冗余不是装饰。

## 边界（必须读）

这套工具证明的是"**包内声明与包内文件一致**"，加上"**公钥在某个时间点前已公开**"。一句话只到这儿。

- 不证明对方的研究结论成立；
- 不证明包本身不是一份自洽的假账。A4 攻击（同时改文件、改期望、改 spine）就是演示这个边界：工具只能报"不一致"，判断不了谁对；
- **不证明持有人身份**：时间锚证明"存在过"，不证明"这是谁"。要做到那层需要域名锚（DANE/TLSA + DNSSEC）或某个别人已认识的指纹；
- 所以对外只能声明**复现性**，不能声明**证实**。

## 另一类证据：门禁自测日志

`evidence/io_selftest_clean_venv.log` 是一份内部发布门禁在空 venv 下的自测输出：11 份被故意注入违规的稿子**全部被拒**，基线通过。这证明"门禁会拒"，而不是"门禁通过了一切"。

门禁源码不在此仓库公开（内含内部词表）。需要独立复跑可以在 issue 里说明用途，我按用途提供只读访问。
