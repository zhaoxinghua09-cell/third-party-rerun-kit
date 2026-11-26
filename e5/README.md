# E5 · Outsider full-suite runner

把「一个账号名下到底有多少仓库能被外人跑出读数」变成可复跑的四档统计，而不是抽样表态。

## 四档口径

| 档 | 判定 | 是否计入 E5 合格 |
|---|---|---|
| 有测试 | 树里存在 pytest / 自研 runner（`tests/run_*.py`、`tests/run.js`）/ JS `test` 脚本 / 可自执行测试脚本 | 是（需真跑通，且测试内有断言或状态比对） |
| 仅自检 | 只有 `check_links.py`、`verify_chain.py` 一类完整性脚本 | **否**：链接没坏不等于被测代码正确 |
| 无校验 | 全树零校验文件 | 否 |
| 缺失/错误 | 无法探测 | 否 |

「有测试」的判定必须扫**全树**，不能只看顶层：测试放在 `service/`、`tools/`、`skills/*/tests/`、`audit/*/` 的仓库会被顶层枚举漏掉。

## 合格线（两条，都满足才算合格）

1. **跑通**：`passed > 0` 且 `failed = 0` 且 `errors = 0` 且 `exit = 0`；
2. **有断言证据**：`passed >= 3` 且测试文件内至少一处非平凡断言（`assert`、`assertEqual` 等）或状态比对（`==`/`!=`）。

只有第 1 条的是「薄证据」——脚本自报通过、测试里零断言，不计入合格。判定算法逐条写在 `reports/assert_decision_algorithm_20261126.md`，第三方可按它独立复算。

## 八件套执行顺序

```bash
python e5_build_manifest.py      # 1. users/{owner}/repos 翻页到底，清单 + commit 锚定
python e5_probe.py               # 2. 顶层结构探测（入口/测试/README）
python e5_deep.py --all          # 3. git/trees/<sha>?recursive=1 全树扫描，三档
python e5_deep_merge.py          # 4. 深层命中升格 + 仅自检标记
python e5_run.py                 # 5. zipball 解包真跑（pytest / 自研 runner / npm test / node --test）
python e5_selfcheck.py           # 6. 仅自检那档真跑（不计合格）
python e5_merge.py               # 7. 回写 manifest
python e5_board.py               # 8. 生成看板 HTML（零外链）
```

证据侧补充脚本：`e5_assert_audit.py`（逐件读测试文件、统计断言并输出样本）、`e5_strict_apply.py`（把严格结论写回 runner）、`e5_sample_log.py`（抽样件完整日志）。

## 复跑前置：依赖预装清单

外部审查要求把「机器上到底要装什么」写明白，否则外人拿到的失败是环境错误，不是代码结论。

| 组件 | 要求 | 不做会怎样 |
|---|---|---|
| Python | 3.9 及以上（本轮实测 3.11.x） | — |
| pytest | 任意近期版本（本轮 8.x） | 测试入口全部失效 |
| Node / npm | Node 22.x（含 `node --test` 支持） | JS 仓库判 not_runnable，如 `agent-governance-vocabulary` |
| 第三方包 | **可变**：按各仓库 `pyproject.toml` / `requirements.txt` 现装（如 `fastmcp>=3.4,<5`、`mcp`、`requests`） | `ModuleNotFoundError`，如 `medxpert-reg-connector` |
| GitHub token | 只读 `repo` scope，仅访问 `api.github.com` | 清单与 zipball 取不到 |
| 网络 | 需要 `api.github.com`；`github.com`/`raw.githubusercontent.com` 可不通 | git 通道不可用，全部改走 REST API |
| 激活虚拟环境 | 建议 `python -m venv` 隔离，避免宿主 pytest 配置干扰 | 裸 `pytest` 可能被树内 `sys.exit(0)` 脚本打断 |

不预装第三方包也能跑：判定器对 `not_runnable` 如实记，不伪装 PASS。但若想让读数可跨机比较，第三方包版本必须两边一致。

## 最新读数（2026-11-26）

- 分母：三账号 254 件（zhaoxinghua09-cell 193 / stevenzhao07 36 / LGD-Eval 25）。
- 四档：61 有测试（48 顶层 + 13 深层）/ 13 仅自检 / 180 无校验 / 0 缺失。
- 执行：61/61 已跑；原始合格 36；**严格合格 33**（变异得分 0.688，22/32 全量）（薄证据 3 件：`fgtida-paris-input-2026`、`skill-improver`、`LGD-Eval/skill-scout`）。
- 累计 passed：3971（公司机）、3862（家机）。两机不跨机加总。
- 严格合格取**两机交集 33**：家机曾判 34，多出的 `skill-improver` 经公司机全树定位 + 人工实核确认 135 行零断言，改判薄。
- 自检档：公司机 6/13（5 ok + 1 经 PR #2 修复后远端复核通过）、家机 7/13。
- 同一 commit 同一 zipball 上，两机有 4 件读数不同，TOP3 根因见 `reports/two_machine_failure_top3_20261126.md`。

## 变异检查：断言会不会抓到 bug

抽样对 A 档 12 件各注入 1 处语义变异（`==`→`!=` 为主），跑测试看是否变红：**全部 33 件严格合格中 32 件可测，22 件 KILLED，得分 0.688**，10 件 SURVIVED，其中 5 件落在 vendored / CI / demo / CLI 脚本上，1 件 SKIP（`regdoc-commons` 无可机械替换节点）。详见 `reports/mutation_check_20261126.md`，原始读数 `readouts/e5_mutation.json`。这是「测试不是摆设」目前唯一可机械复现的证据；但它只覆盖抽样点，不等于整体覆盖率。

## 一键复跑（第三方最短路径）

```bash
pip install pytest
export GH_TOKEN=<只读 token>
python e5_verify_all.py --n 8
```

按 A2/B3/C2/薄1 分层抽样，下载 zipball 真跑，与 `readouts/e5_runner.json` 基线逐件比对，输出 MATCH/DIFF 与匹配率。公司机与家机各跑 8 件，均 **8/8 MATCH（1.0）**；两机样本名单略有不同（分层取前 N 个），差异件（uibc-core 2092/2090、agent-control-standard 901/794）仍会报 DIFF。关键教训：入口写法是最大变量——`pytest <文件列表>` 会收集为空，必须 `pytest tests`；上一版仅因此把 28 条通过变成 0 条。详见 `reports/verify_all_20261126.md`。

## 全量复跑与内容指纹（2026-11-26）

全量 33 件连跑两遍：**树指纹 33/33 SAME（`tree_diff: []`）**，读数 A 遍 33/33、B 遍 32/33；稳定 32 件，flaky 1 件（`aps-conformance-suite`，7 次观测 17/18/19/20）。详见 `reports/full33_fingerprint_20261126.md`。

- `e5_fingerprint.py` — 树指纹：`sha256(sorted "rel_path\tsha256(file)" lines)`，整枝跳过 `.git/node_modules/venv/.venv/dist/build/__pycache__/.tox`
- `e5_manifest_hash.py` — 重算 33 件指纹基线 → `readouts/e5_manifest_hashes.json`
- `e5_verify_all.py --all` — 全量跑：读数 + 指纹双比对，任一 DIFF 或指纹不一致即 exit 1
- 跨机全量：公司机 A 33/33、B 32/33，家机 33/33；三遍指纹均 33/33 SAME（`readouts/e5_verify_full33_home.json`、`reports/cross_machine_full33_20261126.md`）
- 指纹基线已扩到 **36 件**（33 严格 + 3 薄证据）；薄证据 3/3 亦复跑一致，但**可复现不等于有证据**，合格口径仍是 33（`reports/36item_scope_20261126.md`、`board/E5_full33_board_20261126.html`）

**入口规则（唯一口径，别按字母序猜）**：`tests/run*.js` → `node` 跑；否则 `pytest tests`（传目录，不传文件列表）；pytest 收不到用例 → `run*` > `selftest*` > 其它脚本。JS 总入口不是 pytest 覆盖得到的：`regdoc-commons` 的 `run.js` 52 条，而 pytest 只收到 13 条 py 用例。

**负控**：把某件基线指纹改 1 位 → `MATCH_READING_TREE_DIFF` + exit 1（证明指纹比对不是摆设）。

## 已知限制（必须写在读数旁边，不能省）

- **archived 仓库不可写**：`LGD-Eval/silent-failure-catalog` 已归档，自检 fail 的修复只能本地验证（`check-catalog` 已 PASS，15 条），远端需 unarchive 才能落地（本轮已走 PR 后恢复归档）。
- 链接类自检依赖外网：网络受限的机器会把 `check_links` 判成 fail（如 `LGD-Eval/awesome-agent-skills-1`，公司机 fail / 家机 ok）。
- 宿主 pytest 配置可能干扰：树上存在会 `sys.exit(0)` 的脚本时，裸 `pytest` 会被打断，须显式 `pytest tests`。
- 入口假设影响结论：同一件 `LGD-Eval/skill-scout`，走 pytest 是 `no tests ran`（exit 5），直跑 `tests/selftest.py` 是 exit 0。RUNBOOK 已写明必须落入口。
- 「仅自检通过」永远不计合格 —— 否则等于用「文件都在」冒充「代码正确」。
- 断言审计是静态正则：能证明「文件里有断言」，不能证明「断言覆盖了被测逻辑」。变异测试未做。

## 与竞品口径的关系

- **OpenSSF Scorecard `CI-Tests`**：只读 GitHub `CheckRuns`/`Statuses` 的历史痕迹，**不本地跑**。E5 补的是「历史有没有跑过」之外的「现在能不能在外部机器上跑通」。
- **SLSA `verifying-artifacts`**：验 provenance 签名与 builder 绑定，判「产物出自谁」，**不判外人能否跑通**。
- **Reproducible Builds**：验构建确定性（同源码同产物字节）。与 E5 互补——E5 验「跑得出结果」，RB 验「构建得出同一份字节」，E5 未做字节级复现。
- **OpenSSF Best Practices Badge**：自评问卷（是否有测试、是否 CI），不是运行测量。E5 与它的差别就是「填表」与「实跑」。
- **TUF / RFC 6962 CT / C2PA**：分别管更新框架、可审计 Merkle 日志、内容凭证，E5 均未覆盖。

结论：E5 在「外人本地复跑可执行测试」这一格补空白；在 SLSA provenance、TUF、CT 日志、C2PA、RB 字节复现五处明确落后，不冒充。

## 外部审查与相关材料

- `reports/E1_external_ai_review_20261126.md` — 外部 AI（DeepSeek-V3）独立审查，判决 CONDITIONAL PASS，五条件已闭环。
- `reports/assert_decision_algorithm_20261126.md` — 断言判定算法（可复算）。
- `reports/two_machine_failure_top3_20261126.md` — 两机差异 TOP3 根因。
- `reports/uibc_core_drift_20261126.md` — 版本 DRIFT 说明与解除条件。
- `reports/mutation_check_20261126.md` — 全部 33 件变异检查（22/32 KILLED，0.688）。
- `reports/four_layer_ledger_20261126.md` — 四层总账（S/REQ/E/IO 全部 REFUSE，缺口定位到字段）。
- `reports/verify_all_20261126.md` — 一键复跑器（8/8 MATCH 及两次 DIFF 的入口教训）。
- `reports/cross_machine_verify_20261126.md` — 跨机复跑（两机各 8/8，含差异件对照）。
- `reports/full33_fingerprint_20261126.md` — 全量 33 件 + 内容指纹（33/33 同树、三坑归因、32 稳 1 flaky）。
- `reports/E1_handover_pack_20261126.md` — E1 交接包（别人照抄即过，含 prompt 与 JSON 模板）。
- `reports/e_layer_status_20261126.md` — E 层门禁真读数（36 条 REFUSE / 0 PASS）。
- `reports/E5_strict_pass_line_20261126.md` — 严格合格线执行报告。
- `readouts/` — 原始 JSON 读数（含 `e5_assert_audit_company.json` 逐件断言样本）。
- `RUNBOOK_FOR_THIRD_PARTY.md` — 第三方照单复跑的执行单。
