# E5 收尾报告（两机对照版，2026-11-26）

> 生成：2026-11-26 01:25（UTC+8）。家机 = 赵兴华的台式机，公司机 = DESKTOP-IGJBTUB。
> 两机用**同一套脚本、同一套判据、同一份 token 类别**（持证人，无仓库写权限），各自独立跑一遍。
> 数字都能在 `e5_20261125/*.json` 里按 repo 键查到原行。

## 一、结论

E5 不再是"0 件通过"。家机已把**全部 48 个有验证入口的仓库跑满（覆盖率 100%）**：
**32 件合格 / 3822 条测试通过**；公司机侧跑 34 件、26 件合格 / 3760 条通过。
分母由 162 更正为 **254**（三账号全量）。两机结构层读数**完全一致**（254/254 探测、48 件有入口），
执行层读数**故意不同**并分别记录——因为差异正是"外人复跑"要暴露的东西。

## 二、两机同口径读数

| 指标 | 家机 | 公司机 | 判定 |
|---|---|---|---|
| 清单总量 | 254（193/36/25） | 254（193/36/25） | 一致 |
| 结构探测 | 254/254，48 有入口、206 无、0 缺失 | 254/254，48 有入口、206 无、0 缺失 | **一致** |
| 执行层件数 | **48（覆盖 48/48 = 100%）** | 34（覆盖 34/48） | 家机已跑满 |
| 合格件数 | **32** | 26 | 家机更高 |
| 非合格构成 | 3 partial / 3 not_runnable / 10 no_tests_collected | 3 / 1 / 4 | 判定更严后暴露更多 |
| 累计 tests passed | **3822** | 3760 | 家机更高 |
| uibc-core | **2090 / 2 failed** | **2092 / 1 failed** | 两机失败项不同 |
| agent-control-standard | **794 / 20 failed**（maxfail 截断） | **901 / 17 failed** | 同一仓库两套失败集 |

**uibc-core 的两机失败项**（同一 commit、同一 zipball）：

- 家机：`test_resolve_generated.py::test_outside_a_rebase_it_touches_nothing`（`FileNotFoundError`）、
  `test_verify_external_node_report.py::TestItRecomputes::test_quick_run_matches_the_receipt`（quick run 与 receipt 不一致）。
- 公司机：`test_outsider_rerun.py::test_receipt_matches_this_tree`（`FILE COUNT MOVED: receipt 2244, tree 2248`）。

同一仓库在两台机器上失败项不同，说明这些用例对**运行环境与仓库树状态**敏感。这不是噪声，是结论：
**只报一台的读数就是抽样冒充全量**。

## 三、判定器被自己的数据打脸四次（都已修进代码）

| # | 错在哪 | 误判 | 修法 |
|---|---|---|---|
| 1 | 只认 `pytest tests` | `tests/run_golden.py`、`tests/run.js` 类仓库被判"不可运行"（7 件） | fallback 跑仓库自带 runner |
| 2 | 跑通后仍按 `N passed` 取数 | exit 0 全绿被判 `not_runnable`（再 7 件） | 加自定义计数（`N/N PASS`、`PASS N checks`） |
| 3 | fallback 只认 `run*` 前缀 | `tests/test_package_integrity.py` 这类自执行脚本漏掉 | fallback 扩到任一自执行 `.py` |
| 4 | 成功口径只认英文 | `LGD-Eval/skill-scout` 输出"自测全部通过"被判不可运行 | 加中文口径（自测全部通过/全部通过/全绿） |
| 5 | 完全没接 JS 项目的官方入口 | 8 个 `package.json` 仓库一律判"无可执行入口" | 加 `npm test`（有 `scripts.test` 时）与 `node --test` 口径；再逐个核 `scripts` 字段，确认 6 件确实无 test 脚本 |

五次都在重跑后校正。**没有这五次，这张表会多出 20 条假"跑不起来"。**

## 四、对标"最好的"：E5 站哪

| 对照 | 它怎么判 | 与 E5 的关系 |
|---|---|---|
| OpenSSF Scorecard `CI-Tests` | 看 GitHub `CheckRuns`/`Statuses` 过去约 30 次提交有无名字含 `github-actions`/`test` 等的 CI 成功运行；不本地跑 | E5 更硬：本地下载+解包+执行并取 passed/failed；Scorecard 在被"CI 跑过但外人跑不起来"的仓库上仍可能满分 |
| SLSA `verifying-artifacts` / `slsa-verifier` | 验 provenance 签名、builder 身份在信任名单、artifact 摘要与 provenance 一致；`builder.id` 未被签名绑定则报 unproven | 互补不重叠：SLSA 判"产物出自谁"，不判"外人能否跑通" |

结论：在"外人本地复跑并通过"这一维度，E5 的做法比 Scorecard CI-Tests 更严格；但换不来 SLSA 的签名信任层，
两者必须并列写，不能互相冒充。

## 五、差在哪（不粉饰）

**先看非合格的 16 件（家机，全部实名可查）**

| 类别 | 件数 | 仓库 | 根因 |
|---|---|---|---|
| `partial` 真跑有失败 | 3 | uibc-core、agent-control-standard、lgd-theory | 收据/树漂移、Windows 无 POSIX symlink、文档标题与 source.toml 路径 |
| `not_runnable` | 3 | medxpert-reg-connector（缺 `fastmcp`）、agent-governance-vocabulary（`npm test` 链上 Node 报错）、dsh-plugin-lgd-trust（`node --test` 有 fail） | 未声明依赖 / 脚本顺序依赖 |
| `no_tests_collected` | 10 | synomosai-governance-mcp、medxpert-library-connector、medxpert-standards-connector、fhir（pyproject 无用例）；LGD-Eval、governanceos、dsh-secret-leakage-scan、whois-agent、medxpert-reg-hub、attestation（`package.json` 无 `test` 脚本，已逐个核过 scripts 字段） | 仓库自身缺用例 |

**JS 类的核实结论**：npm 10.9.8 与 node v22.23.2 在本机可用；6 个 JS 仓库的 `package.json` 里
`scripts.test` 为空或不存在（只有 `selftest`/`lint`/`format`），不是我们漏判——**是这些仓库没有外人可执行的测试入口**。

| 缺口 | 现状 | 谁能补 |
|---|---|---|
| 公司机未跑满 | 公司机跑 34/48，家机已 48/48 | 按家机同一 `--repos` 清单补跑剩余 14 件（约 15 分钟） |
| 4 件零收集（pyproject） | 无用例 | 仓库 owner 补最小用例（写动作，需批准） |
| 1 件缺依赖 | `medxpert-reg-connector` 缺 `fastmcp` | owner 补依赖声明（写动作） |
| uibc-core 收据漂移 | 公司机报 `receipt 2244 / tree 2248` | 修收据属写动作，需 owner 批准 |
| **"陌生人"空位** | 本轮执行者是持证人本人 | 只能等无利益关系第三方；属 E2 缺口，不因本轮实测消失 |
| 归档仓库计入分母 | 254 含 `archived` | 口径问题，需 owner 定 |

## 六、复现

```powershell
cd D:\Workbuddy\00-总控台\发布前审查
# 家机：token 由 ucvault 提供；公司机：$env:GH_TOKEN = (& "D:\标准\vault\get_github_pat.ps1" -Account zhaoxinghua09-cell).Trim()
python e5_build_manifest.py            # → 254
python e5_probe.py                     # → 254/254，48 有入口（约 70 秒）
python e5_run.py --repos zhaoxinghua09-cell/uibc-core ...   # 单仓 6–8 分钟
python e5_merge.py ; python e5_board.py
```

## 七、需要 owner 批准的写动作（本轮一律没做）

1. 修 `uibc-core` 收据（`FILE COUNT 2244 → 2248`）并重跑 `test_outsider_rerun`；
2. 给 `medxpert-reg-connector` 补 `fastmcp` 依赖声明；
3. 给 7 个零入口仓库（4 个 pyproject + 3 个 JS）补最小用例与 `scripts.test`；
4. 把 E5 五件套（build/probe/run/merge/board）与两份报告推到远端（本机 `github.com` 页面不可达，推送属写动作）；
5. 公司机补齐剩余 14 件（按家机同一 `--repos` 清单，约 15 分钟），使两机覆盖对齐 48/48。
