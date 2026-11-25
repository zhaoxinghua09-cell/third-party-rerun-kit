# 第三方复跑工具包（rerun kit）

用途：有人请你"以第二个独立方身份复跑一段验证链"时用这套跑。**默认不执行对方代码**，只核对对方声明；要重建才显式 `--execute`。

## 三个能力，分三层（别混着说）

| 层 | 工具 | 回答什么 | 不回答什么 |
|---|---|---|---|
| 完整性 | `verify_chain.py` | 包内声明与包内文件是否一致 | 这些内容是谁做的、结论是否成立 |
| 真实性 | `verify_chain.py` 的 signature 段 | 有没有签名、能不能用 cosign 验 | 我们不内置验签算法，验不了就是 INCOMPLETE |
| 确定性 | `determinism.py` | 同一包跑两次，产物是否一致 | 结论对不对（只证明"可重复出现"） |

## 退出码（照这个读，别猜）

| 码 | 含义 |
|---|---|
| 0 | PASS：全部检查通过（声明了签名也必须真验过） |
| 2 | 参数/manifest 问题，或 `determinism.py` 未加 `--execute` |
| 3 | FAIL：硬性检查不通过（篡改、夹带、链断、覆盖率不足、签名文件缺失） |
| 4 | **INCOMPLETE**：包本身没查出问题，但**我们验不了**（如声明了 sigstore bundle 而本机没装 cosign）。**不是 PASS** |

第 4 条是最容易被人含糊掉的地方：**"验不了"不等于"包错了"，也绝不等于"通过"**。宁可给不完整结论，也不给假 PASS。

## 文件

| 文件 | 作用 |
|---|---|
| `verify_chain.py` | 复跑器：16 项检查（结构/覆盖/哈希长度/白名单/逐文件/逐步骤/期望输出/签名） |
| `redteam.py` | 对复跑器自身红队，8 攻必须全部被拦或判 INCOMPLETE |
| `make_demo_pkg.py` | 造合成包；`--unstable` 造"写入时间戳"的非确定包作对照 |
| `determinism.py` | 重复运行分级：byte-identical / near-identical / unstable |
| `demo_producer.py` | 演示重建器（从 inputs 重算 outputs） |

## 用法

```powershell
python make_demo_pkg.py                 # 确定性包（outputs 由 producer 真跑生成）
python make_demo_pkg.py --unstable      # 非确定包（写入当前时间）
python verify_chain.py --pkg demo_pkg --json demo_run.json
python redteam.py                       # 8 攻
python determinism.py demo_pkg --execute --out determinism_stable.json
python determinism.py demo_pkg_unstable --execute --out determinism_unstable.json
```

## 已实跑（2026-11-25）

- 基线：**16/16 PASS**，exit 0
- 红队 8 攻：**8/8 拦下**；A8（签名自洽但本机无 cosign）正确判 **INCOMPLETE / exit 4**
- 确定性：确定性包 `byte-identical`；写入时间戳的包 `unstable`（分级确实能分辨）
- 干净环境（空 venv 仅 pip、代理指向黑洞、无密钥）：与主环境逐字节一致

## 边界（照抄，别改口气）

- 只证明"包内声明与包内文件一致"。任何人可造一份自洽 manifest，我们判不了是谁做的——要真实性得靠 cosign/in-toto；本工具只负责把"能不能验"如实标出来。
- `determinism.py` 会执行 producer，属"跑对方代码"。默认拒绝，必须 `--execute`，前提是你已读过那段代码。
- 重建演示用的是**我们自己的合成包**，不是任何第三方软件构件的重建。

## 红队历史（不抹掉）

1. 第一版 6 攻时 **A6 逃逸**：把 `steps` 抽空，旧版仍判 PASS、exit 0。修法加 structure / coverage / hash-length 三条硬门；修完立刻发现自己的 demo 包不合格（有未覆盖文件），**补包而不放宽规则**。
2. 扩到 8 攻时发现语义错位：A8 一开始被判 `FAIL(3)`，而"验不了"应是 `INCOMPLETE(4)`，已改。
