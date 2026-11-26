# 变异检查（扩至 A+B 两档 30 件）：断言存在 ≠ 断言有效

上一轮只测了 A 档 12 件（得分 0.818）。这一轮把范围扩到 **A+B 两档**，即 passed ≥ 6 的全部严格合格件，样本从 11 件可测扩大到 30 件。

方法是变异测试：往实现代码注入一处语义改变，跑测试。测试变红 = 这处逻辑被覆盖（KILLED）；照样绿 = 没抓到（SURVIVED）。

## 一、读数（2026-11-26 08:33，公司机）

| 指标 | 值 |
|---|---|
| 纳入 | A+B 档 31 件（passed≥6 且跑通） |
| 剔除 | 1 件薄证据（`skill-improver`，无断言，不参与） |
| 有效 | **30 件** |
| KILLED | **22** |
| SURVIVED | **8** |
| SKIP | 1（`regdoc-commons`，12 个实现文件无可机械替换节点） |
| **变异得分** | **22/30 = 0.733** |

对比上一轮 A 档 12 件：9/11 = 0.818。样本翻近三倍后得分降到 0.733——**A 档（测试条数多的件）确实比 B 档更能抓住 bug**，说明分层本身是有意义的，不是凑数。

## 二、SURVIVED 8 件的性质（这一轮最有信息量的部分）

| 仓库 | 变异点 | 性质 |
|---|---|---|
| zhaoxinghua09-cell/uibc-iverify | `ivcli.py` return 3→4 第 28 行 | 主模块边缘分支 |
| zhaoxinghua09-cell/wexp-check | `scripts/compare_corpora.py` 第 23 行 | CLI 工具脚本 |
| zhaoxinghua09-cell/silent-failure-catalog | `demo_tamper_check.py` 第 31 行 | 演示脚本 |
| zhaoxinghua09-cell/skillgate | `alert.py` 第 65 行 | 主模块告警分支 |
| zhaoxinghua09-cell/awesome-claude-skills | `document-skills/docx/ooxml/scripts/pack.py` 第 147 行 | **vendored 第三方脚本** |
| LGD-Eval/lgd-gate | `ast_analyzer.py` 第 89 行 | 主模块分析器 |
| LGD-Eval/awesome-claude-skills | `.github/link-check/check_links.py` 第 83 行 | CI 辅助脚本 |
| LGD-Eval/awesome-llm-skills | `document-skills/docx/.../pack.py` 第 147 行 | **vendored 第三方脚本** |

**8 件里 6 件的变异落在 demo / CLI 脚本 / vendored 第三方代码 / CI 脚本上**，只有 `uibc-iverify` 与 `skillgate` 落在主模块。含义清楚：这些仓库的测试围着「核心库」建，边缘脚本与引入的第三方代码无人覆盖——但它们是仓库的一部分，外人同样会下载、同样可能坏。

这不掩盖，是如实暴露。

## 三、SKIP 1 件

`regdoc-commons`：12 个候选实现文件里没有 `Compare(Eq)` 或 `Return(常量)` 可机械替换。这套算子（Eq→NotEq、常量 +1、And↔Or）对它不适用，需人工设计语义变异（删一段校验、改一个正则）。

## 四、局限（必须与读数一起出现）

1. **1 个变异点 ≠ 覆盖率**。0.733 只表示「30 个抽样点里 22 个被抓住」，不能外推成「73% 代码被测」。
2. 命中位置由文件遍历顺序决定，落在边缘脚本就报边缘脚本，不做挑选美化。
3. 死代码命中记 SURVIVED（本就无人测，正确）。
4. 只做单点、单算子，是最弱检验；真正的变异测试会为每件生成几十个变异体。

## 五、三层证据的现状

| 层 | 读数 | 覆盖范围 |
|---|---|---|
| 能不能跑 | 61/61 实跑 | 全部有测试入口的件 |
| 有没有断言 | 33 件严格合格（薄 3 剔除） | 36 件原始合格 |
| **断言会不会抓 bug** | **22/30 KILLED（0.733）** | A+B 两档 30 件 |

三层都是「抽样 + 可复算」，都不冒充全量覆盖率。第三层是目前唯一能证明「测试不是摆设」的机械证据。
