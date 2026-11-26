# 变异检查：33 件严格合格全部做完（22/32 会变红）

前两轮分别测了 A 档 12 件（0.818）、A+B 档 30 件（0.733）。这一轮把**全部 33 件严格合格件**都做了，覆盖从抽样变为全量。

方法是变异测试：往实现代码注入一处语义改变，跑测试。变红 = 该处逻辑被覆盖（KILLED）；照绿 = 没抓到（SURVIVED）。

## 一、读数（2026-11-26 08:36，公司机）

| 指标 | 值 |
|---|---|
| 严格合格件 | 33 |
| 可测（有 Python 测试与可变异实现文件） | **32** |
| KILLED | **22** |
| SURVIVED | **10** |
| SKIP | 1（`regdoc-commons`，无可机械替换节点） |
| **变异得分** | **22/32 = 0.688** |

三档递进：A 档 0.818（12 件）→ A+B 0.733（30 件）→ 全量 0.688（32 件）。**范围越大得分越低**，因为 C 档（passed 3–5 条）覆盖本就薄。这本身证明分层有效：条数少确实更容易漏。

## 二、SURVIVED 10 件的性质分布

| 类型 | 件数 | 明细 |
|---|---|---|
| vendored 第三方脚本 | 2 | `awesome-claude-skills` 与 `LGD-Eval/awesome-claude-skills` 的 `document-skills/docx/ooxml/scripts/pack.py`（同一份原版代码） |
| CI / 链接检查脚本 | 1 | `LGD-Eval/awesome-claude-skills` 的 `.github/link-check/check_links.py` |
| demo 演示脚本 | 1 | `silent-failure-catalog` 的 `demo_tamper_check.py` |
| CLI 工具脚本 | 1 | `wexp-check` 的 `scripts/compare_corpora.py` |
| **主模块** | 5 | `skillgate` alert.py、`uibc-iverify` ivcli.py、`LGD-Eval/lgd-gate` ast_analyzer.py、`evaluation-evidence` 两份镜像的 verify_hash_manifest.py |

**10 件里 5 件落在非核心脚本上**（vendored / CI / demo / CLI），5 件落在主模块边缘分支。上一轮这个比例是 6/8，这轮降到 5/10——C 档件的薄弱更多出现在主模块本身。

`evaluation-evidence` 那件值得单说：变异把 `verify_hash_manifest.py` 的 `return 2` 改成 `return 3`，测试依然全绿。校验脚本的返回码分支没被断言覆盖，说明它验的是「能跑」，不是「返回码对不对」。这类缺陷用「有没有 assert」查不出来，只有变异能查出来。

## 三、SKIP 1 件

`regdoc-commons`：12 个候选实现文件里没有 `Compare(Eq)` 或 `Return(常量)` 可机械替换，需人工设计语义变异。

## 四、局限

1. 1 个变异点 ≠ 覆盖率；0.688 不能读成「69% 代码被测」。
2. 命中位置由文件遍历顺序决定，落在边缘文件就报边缘文件。
3. 死代码命中记 SURVIVED（正确）。
4. 单点单算子是最弱检验；真正的变异测试会为每件生成几十个变异体。

## 五、三层证据（最终口径）

| 层 | 读数 | 覆盖 |
|---|---|---|
| 能不能跑 | 61/61 实跑 | 全部有测试入口的件 |
| 有没有断言 | 33 件严格合格（薄 3 剔除） | 36 件原始合格 |
| **断言会不会抓 bug** | **22/32 KILLED（0.688）** | 33 件严格合格，全量 |

第三层已从抽样变成全量，是目前唯一能证明「测试不是摆设」的机械证据。
