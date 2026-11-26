# E5 收尾总报告（2026-11-26，公司机 DESKTOP-IGJBTUB 实测）

> 本报告是本轮收尾件。原则：能跑的说跑过的数，跑不动的说卡在哪，不把"做了"写成"超越了"。

## 一、一句话结论

E5 从"0 件通过"推进到 **254 件全量入册、61 件可验、61/61 实跑、33 件严格合格（另 3 件薄证据不计）、两台机器互证**，
四项写动作全部落到远端并可复核；但在"全面超越竞品"这件事上，只能在**"外人本地复跑"这一格**说超越，
其余维度（外部锚不可否认、更新框架、公开日志、内容溯源）我们没有实现，也没有声称。

## 二、硬读数（本机实测，2026-11-26）

| 指标 | 数值 | 口径 |
|---|---|---|
| 入册仓库 | 254（193 / 36 / 25） | `users/{owner}/repos` 翻页到底，非抽样 |
| 有测试 | 61（48 顶层 + 13 深层） | 全树 `git/trees?recursive=1` 扫描 |
| 仅自检 | 13 | 只有 check/verify 类脚本，**不计合格** |
| 全树零校验 | 180 | 仓库自身缺陷 |
| 执行层 | **61/61（100%）** | zipball 解包真跑，无 `.git`、无凭证 |
| 合格（严格） | **33**（另有 3 件薄证据不计；原始合格 36） | passed≥3 且测试内含断言或状态比对；原 36 件中 2 件（1 条通过、测试无断言）降为薄证据，见第十节 |
| 累计 passed | **3971** | 公司机；家机 3862 |
| 自检档 | **6/13 通过**（5 + 1 修复后通过） | 公司机实测；家机 7/13（6 + 1） | 两机均为实跑，结构已统一为 ok / ok_after_fix / fail |

## 三、四项写动作（全部已落地）

| # | 动作 | 结果 | 证据 |
|---|---|---|---|
| 1 | uibc-core 收据 | main 已更新，`files_hashed` 2244 → 2248 | `6cdde5468a` / `87738fe978`；本地 `test_outsider_rerun` 5 passed（家机 20.71s、公司机同项亦 5 passed，两机各跑一次）；远端 zipball `--check` exit 0 |
| 2 | fastmcp 依赖 | 无需改仓库（早已声明 `fastmcp>=3.4,<5`） | 本机 fastmcp 4.2.0；`tests/selftest_stdio.py` exit 0（7 tools / 27 hubs / 15 sources） |
| 3 | LGD-Eval 镜像 | 解除归档 → 分支 → **PR #2** → squash `a22d1a68` → 恢复归档 | 本机对合并后 main 跑 `check-catalog` exit 0，15 条全索引 |
| 4 | 八件套与报告 | 已推送 | `third-party-rerun-kit` 的 `e5/` 目录，最新 `0c1dc2f1` |

## 四、竞品对标：哪些格真超越，哪些格我们落后

| 维度 | 对标物 | 它判什么 | 我们 | 结论 |
|---|---|---|---|---|
| CI 是否跑过测试 | OpenSSF Scorecard `CI-Tests`（读 CheckRuns/Statuses 历史） | 平台侧的运行痕迹，不本地跑 | 本地下载+解包+执行，取 passed/failed | **超越**：它看不到的"本地跑不通"我们能看见；但它有 18+ 检查项并被广泛采用，我们只有这一格 |
| 产物出自谁 | SLSA `verifying-artifacts`（验签名与 builder 绑定） | provenance 签名、builder identity、摘要匹配 | 未做签名验证 | **落后**（且不重叠，属互补） |
| 抗密钥妥协的更新 | TUF 规范（root/targets/snapshot/timestamp 四角色） | 元数据角色与阈值签名 | 未实现更新框架 | **落后** |
| 不可否认的公开日志 | RFC 6962 Certificate Transparency（Merkle 树 + 审计路径） | 公开可审计、防篡改 | 单链收据，无公开日志 | **落后** |
| 内容溯源 | C2PA 2.x（Manifest + 硬绑定哈希 + TSA 时间戳） | 媒体来源与编辑历史 | 未涉及 | **落后** |

**所以"全面超越"不成立**：四格落后、一格超越。可以成立的说法是——
在"由外部机器在干净副本里把 254 个仓库逐个跑出读数"这件事上，公开的同类工具里没有对等物；
Scorecard 只读 CI 痕迹，SLSA 只判产物血统，两者都不回答"外人能不能跑通"。

## 五、门禁现状（不粉饰）

| 项 | 状态 |
|---|---|
| E1 外部 AI 审查 | FAIL（未拿到独立审查结论） |
| E2 无利益第三方 | **MISSING**：执行者仍是持证人本人，多跑几轮不会改变 |
| E5 外人全量实测 | 已读数（61/36，双机） |
| 站位门禁 | **REFUSE**：`standing_check.py` verdict=PROBLEMS，`ADMISSION=REFUSE`，`can_stake_new=false` |
| uibc-core 版本 | **DRIFT 保持可见**：登记 0.2.1（DOI 对应）/ 仓库 0.5.0 / citation 0.4.2 |

**DRIFT 为什么不修**：登记册 `standing.json` 的 `drift_note` 已写明，三处统一需要**用户本人在 Zenodo 建新 version**
（`10.5281/zenodo.22821835` 是 0.2.1 的 DOI），AI 不能代做。擅自把登记版本改成 0.5.0，
等于对外宣称"0.5.0 已归档并站位"，那是假主张，因此保持 DRIFT 可见。

## 六、可复核入口

- 工具链与读数：`https://github.com/zhaoxinghua09-cell/third-party-rerun-kit/tree/main/e5`
- 收据修复：`https://github.com/zhaoxinghua09-cell/uibc-core/commit/6cdde5468a`
- 镜像修复 PR：`https://github.com/LGD-Eval/silent-failure-catalog/pull/2`（合并 `a22d1a68`）
- 复跑命令：`python e5_build_manifest.py` → `e5_probe.py` → `e5_deep.py --all` → `e5_deep_merge.py` → `e5_run.py` → `e5_selfcheck.py` → `e5_merge.py` → `e5_board.py`

## 七、逐件证据附录

`e5/board/E5_evidence_appendix_20261126.html`：61 张卡，每张一个仓库、一个 commit 前 12 位、入口文件、
真实输出尾四行、passed/failed/errors/exit/耗时/解包字节。零外链、零 a 标签。
作用：让"36 件合格"变成 36 条可以逐条核的证词，而不是一个数字。

## 八、E1 外部 AI 通道：本轮实测不可用（不算通过）

本机保险库里能用的两家模型通道都做了真实请求：

| 通道 | 结果 |
|---|---|
| dashscope（qwen-plus） | HTTP 403 |
| hunyuan（hunyuan-turbos-latest） | HTTP 401 |

结论：**E1 仍是 FAIL**。不能因为"试过了"就写成"审过了"。
另：hunyuan 那条在测试时因异常消息回显了凭证内容，已单独记在 `e5/reports/E5_credential_exposure_20261126.md`
（仅本地日志、未外发、未进任何提交），并建议你轮换该 key、把多行合并存储的凭证拆成字段。

## 九、明确不做 / 不做假

- 不把"仅自检通过"算进 36 件合格；
- 不把两机推算值当成实测值（家机 7/13、公司机 6/13 都是各自实跑）；
- 不用一次成功的 run 掩盖 14 件 no_tests_collected 与 8 件 not_runnable；
- 不在没有外部证据时新开"我方贡献"站位。

## 十、合格线自审（本轮新增，对自己开刀）

E5 的合格线没有条数下限，于是「1 条测试」也能算合格。按 passed 条数分层后：A≥20 → 12 件，B 6-19 → 19 件，C 3-5 → 3 件，D 1-2 → **2 件**。

因此准确的说法是「**34 件强合格 + 2 件薄证据**」：(1) fgtida-paris-input-2026 的测试文件自述「只验结构与可重建性前提，不验内容是否正确」；(2) LGD-Eval/skill-scout 为 127 行行为自测、0 个 assert、仅 1 条通过。

`verdict` 未回改，只加 `evidence_tier` 与 `manual_review_note`；看板与逐件附录已显示强度列。完整推理见 `e5/reports/E5_pass_line_self_audit_20261126.md`。建议的改法（合格线加 passed≥3 + 断言存在，D 档强制人工复核）**已执行**：重算后严格合格 34、薄证据 2，详见 `e5/reports/E5_strict_pass_line_20261126.md`。

## 十一、外部 AI 审查（E1）拿到之后

E1 此前一直 FAIL（本机两家模型通道 401/403）。本轮在公司机走通 SiliconFlow / `deepseek-ai/DeepSeek-V3`，**判决 CONDITIONAL PASS**，五条件已全部闭环：10% 抽样原始日志（4 件=11.8%，含环境快照）、断言判定算法、uibc-core DRIFT 说明、README 依赖预装清单、两机差异 TOP3 根因。

它没有替我背书，反而逼出一处真错误：审查要求"剔除只能靠 `assert True` 撑着的案例"，逐件复核后发现 `zhaoxinghua09-cell/skill-improver` 的 `tests/run_golden.py` 135 行零断言、零比对，9 条通过全是脚本自报。合格数因此从 34 降到 **33**，两机口径也由此统一（家机 34 / 公司机 33 的差集正是这一件）。

竞品对标同时被收紧：原写"一项超越"，审查指出 Scorecard 覆盖 CI 历史完整性而 E5 不覆盖，并点名遗漏的 Reproducible Builds（字节级构建复现）与 OpenSSF Best Practices（自评问卷）。现在的准确表述是：**E5 只在"外人本地复跑可执行测试"这一格补空白，在 SLSA provenance、TUF、CT 日志、C2PA、RB 字节复现五处落后。**

留给下一轮的三件事（本轮明确不做）：A 档 12 件的变异测试（改实现看测试是否变红）、无利益第三方照 RUNBOOK 实跑、Zenodo 新版本消 uibc-core DRIFT。
