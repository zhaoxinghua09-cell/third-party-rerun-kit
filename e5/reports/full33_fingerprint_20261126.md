# 全量 33 件复跑 + 内容指纹（2026-11-26，公司机）

## 一句话结论

**同一棵树，被证明是同一棵；跑出来 33/33 一次、32/33 一次。稳定的 32 件，不稳定的是 1 件，而它不稳定是因为它自己的测试不稳定，不是机器。**

- 树指纹：连跑两遍，**33/33 件 SAME**（`tree_diff: []`）
- 读数：A 遍 **33/33 MATCH**；B 遍 **32/33 MATCH**
- 唯一不稳定件：`zhaoxinghua09-cell/aps-conformance-suite`，7 次观测得到 17 / 18 / 19 / 20 四种读数

这三件事要一起看才成立。单看"33/33"是自证；配指纹和负控才是可验。

## 1. 内容指纹：先证"是同一棵树"

复跑器原先只比 `passed` 条数。条数一致时仍有漏洞：**拿到的可能是另一棵树**（分支被推、zipball 被换）。所以加一层指纹。

算法（写死，两处共用 `e5_fingerprint.py`）：

1. 目录整枝跳过 `{".git","node_modules","venv",".venv","dist","build","__pycache__",".tox"}`
2. 逐文件取 `相对路径(正斜杠) + TAB + sha256(全文)`
3. 行按字典序排序，`\n` 连接，再取 sha256

基线 `e5/readouts/e5_manifest_hashes.json`：33 件，全部成功算出指纹。

**跳过 node_modules 的代价要写明**：`uibc-core` 全树 2248 文件，指纹口径只覆盖 202 件。指纹证明的是"源码树一致"，不是"整包一致"。

**负控（证明它不是摆设）**：把 `lgd-skill-review` 的基线指纹改 1 个十六进制字符，复跑立刻输出 `MATCH_READING_TREE_DIFF / hash_status=DIFF / exit=1`。改回即恢复。否则这一整套读数作废。

## 2. 三个坑：每一个我一开始都算错了账

这一节比数字重要。三件全部是"同 commit、同 zipball、同机器"，读数却不同。第一版复跑器把三个都判成"环境差异"，追下去发现**三个都是复跑器自己的问题（第三个除外，是仓库自己的问题）**。

### 坑一：测试名里带 FAIL，被判成失败

`stevenzhao07/doc-translate-keep-layout` 基线 40，复跑 0。

实际输出末行是 `40/40 通过`，与基线一字不差。旧判据里有一句 `if "FAIL" in up: return None`，而该仓有一条测试叫 `T09_MISSING_TERMS_FAILS_CLOSED`（"缺术语必须失败关闭"——名字里带 FAIL 才是正确语义）。子串命中，整件被判失败，`passed` 记 0。

修正：不再看 FAIL 子串，只认真实失败计数 `(\d+) FAILED|FAILURES` 且 > 0，以及 Traceback。

### 坑二：仓库有 JS 总入口，pytest 只看到 Python 子集

`stevenzhao07/regdoc-commons` 基线 52，复跑 13。

`tests/` 下有 `run.js`、`rules.js`、`e2e.js`、`xlsx.py`。基线跑的是 `node tests/run.js` → `PASS 52 checks`。复跑器只认 `.py`，pytest 收集到 `xlsx.py` 里 13 条 py 用例 → 13。

修正：`tests/` 下有 `run*.js` 时先用 node 跑它；`.js` 与 `.py` 同等作为入口候选。修后 52，与基线一致。

顺带一条：这个仓库有**两套入口、两套读数**（52 与 13、另外 `rules.js` 还有 44）。所以"读数是几"必须先说清"用哪个入口"，否则任何比较都无意义。

### 坑三：仓库自己的测试就不稳定

`zhaoxinghua09-cell/aps-conformance-suite`：基线 20，同一棵树连跑 7 次得到 20 / 17 / 19 / 17 / 20 / 20 / 18。

这不是环境差异，是**用例本身 flaky**（并发/时序/外部状态）。它进不了"稳定可复现"集合，它的 20 也不该被当硬证据用。修它要改上游测试，不在我这边动手。

**三个坑的教训是同一条：树一致而读数不一致时，先怀疑工具，再怀疑环境，最后才怀疑仓库；而"仓库"里也可能有心跳不稳的测试。**

## 3. 入口规则（唯一口径，别人照这个跑）

顺序固定，不再按"字母序第一个"这种偶然规则：

1. `tests/run*.js` 存在 → `node` 跑它
2. 否则 `pytest tests`（**必须传目录，不传文件列表**：传列表进不到 `conftest.py` 与相对导入，收集为空，这是上一轮 3/8 的根因）
3. pytest 收不到用例（exit 3/5 或 0 条）→ 依次尝试 `tests/run*`、`tests/selftest*`、`tests/` 下其它 `.py`/`.js`

脚本判据：只认 `N/N 通过`、`PASS N checks`、`OK:` 这类正向计数与真实失败计数。

## 4. 稳定与不稳定的边界

`e5/readouts/e5_stability.json`：`stable_count=32`、`flaky_count=1`，flaky 附完整观测序列。

这条边界对外说清楚比说"33/33"更值钱：**32 件是"别人一条命令能验、两次能对上"的；1 件只能说"多数时候是 20"。**

## 5. 这套东西比竞品强在哪、差在哪

| 维度 | Reproducible Builds | OpenSSF Scorecard | 本套（E5 复跑器） |
|---|---|---|---|
| 独立复跑 | 是（构建） | 部分（评分脚本） | 是（下载即跑） |
| 证据可比 | 产物字节 | 分数 | 源树指纹 + 读数 + 负控 |
| 抖动披露 | 不强制 | 不披露 | **单列 flaky 件与观测序列** |
| 覆盖深度 | 构建产物 | 仓库配置 | 测试读数（非构建产物） |
| 缺口 | — | — | 不做构建产物字节一致；指纹不覆盖 node_modules |

**明确不超越的两点**：① 我没有做到"构建产物字节一致"（那是 RB 的核心，需要可确定的构建环境）；② 指纹只覆盖源码树，排除了依赖目录。凡引用本套读数，这两条必须一起说。

## 6. 复算命令（任何人可跑）

```
export GH_TOKEN=<只读 token>
python e5_fingerprint.py                 # 单件：python -c "import e5_fingerprint as f;print(f.manifest('<root>'))"
python e5_manifest_hash.py               # 重算 33 件指纹基线
python e5_verify_all.py --all            # 全量 33 件：读数 + 指纹
python e5_verify_all.py --repos owner/a  # 指定件
```

退出码：0 = 读数全 MATCH 且指纹零差异；1 = 有 DIFF（`MATCH_READING_TREE_DIFF` 也返回 1）。

## 7. 局限（写在明面上）

- 全量 33 件只覆盖"严格合格层"。薄证据 3 件、全树零校验 180 件未纳入。
- 指纹依赖 commit 定址：commit 由 GitHub 保证不可变，但"作者当初提交的就是这棵树"不在本套证明范围内。
- flaky 判定基于 7 次观测，不是统计意义上的稳定度估计。
- 本轮仍未触碰 E1 / E2 / S10 / S11 / L3 这五项"需要另一个人"的门禁。
