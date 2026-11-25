# E5 终版：三档口径封口（家机，2026-11-26 02:00）

> 家机生成。口径：持证人 token、只读、只跑、只记录；不使用仓库写权限。
> 本报告是 E5 的最后一次口径收敛——不再改判据，只把"能不能验"说清楚。

## 一、三档口径（这是本轮的实质变化）

上一轮把"顶层看不见的深层测试"挖了出来（48 → 61）。这一轮追问一句：**剩下 193 件真的什么都没有吗？**

答案分三档：

| 档 | 件数 | 含义 | 是否计入 E5 合格 |
|---|---|---|---|
| 有测试 | **61** | 全树存在 test_*/spec/_test/run*/conftest | 计入（已 61/61 实跑） |
| 仅自检脚本 | **13** | 只有 check_/verify_/validate/selftest 类脚本 | **不计入**（自检 ≠ 测试套件） |
| 什么都没有 | **180** | 全树无任何可执行校验 | 不适用（结构缺陷） |

13 件"仅自检"实名：`third-party-rerun-kit`（`rerun/verify_chain.py`）、`evaluation-protocol`（`verify_vtl.mjs`）、
`assayance`（`tools/check-doctrine.py`）、`memory-interop-vectors`（`retention/check_retention.py` 等）、
`nti-spec`、`publish-quality-gate`（`scripts/check_release.py`）、`medical-ai-toolkit`（`check_portal.py`）、
`silent-failure-catalog`（5 个 check 脚本）、`awesome-healthcare-agents`、`wg2-ibea-charter`、`awesome-agent-skills-1`、
以及两处同名镜像。

**为什么不把它们算合格**：E5 的语义是"外人能复跑并通过测试"。`check_links.py` 通了只说明链接没坏，
`check_catalog.py` 通了只说明目录一致——它们证明不了被测代码正确。把自检当合格，就是拿格式检查冒充功能验证。

## 二、封口读数

| 指标 | 数值 |
|---|---|
| 清单 | 254（193/36/25） |
| 结构层（三档） | 61 有测试 / 13 仅自检 / 180 无 |
| 执行层 | **61/61（100%）** |
| 合格 | **36 件** |
| 累计 tests passed | **3862** |
| 非合格 | 3 partial / 14 no_tests_collected / 8 not_runnable |

## 三、六次纠正之后，这次不是纠正

前六次都是判定器出错（pytest-only、计数口径、`run*` 前缀、英文口径、JS 入口、顶层盲区），改完读数会变。
这一次**没有改任何判据**，只是增加了一档如实分类，让"180 件什么都没有"这个断言有依据——
原来的 193 件里混着 13 件"能跑但没有测试"的仓库，混着说就把两件事说成一件。

## 四、对标仍然成立

| 对照 | 判定对象 | 关系 |
|---|---|---|
| OpenSSF Scorecard `CI-Tests` | CI 里有没有跑过测试（看 CheckRuns/Statuses） | E5 更硬：本地下载+解包+执行取 passed/failed |
| SLSA `verifying-artifacts` | 产物出自哪个 builder、签名是否可信 | 互补：SLSA 不判"外人能否跑通" |

## 五、还差什么

| 缺口 | 现状 | 谁能补 |
|---|---|---|
| **"陌生人"空位** | 执行者仍是持证人本人 | 只能等无利益关系第三方（E2），本轮不能替代 |
| 13 件仅自检 | 单列，未跑 | 若要跑，需逐个装依赖；跑了也不计合格 |
| 180 件零校验 | 结构缺陷 | 仓库 owner 补测试 |
| 25 件非合格 | 依赖/夹具/命名 | 仓库 owner（写动作，需批准） |
| 公司机三档口径 | 公司机仍是两档（61/193） | 在公司机重跑 `e5_deep.py --no-entry` + `e5_deep_merge.py`（约 1 分钟） |
| uibc-core 收据 | 原 `receipt 2244 / tree 2248` | **已于 2026-11-26 修复并推 main**（见第八节） |

## 六、复现（七件套）

```powershell
cd D:\Workbuddy\00-总控台\发布前审查
python e5_build_manifest.py    # 254
python e5_probe.py             # 顶层：48 有入口
python e5_deep.py --no-entry   # 全树三档：61 有测试 / 13 仅自检 / 180 无
python e5_deep_merge.py        # 落盘三档标记
python e5_run.py --skip-done   # 执行层
python e5_merge.py ; python e5_board.py
```

## 七、待 owner 批准的写动作（2026-11-26 已获批并执行，见第八节）

1. 修 `uibc-core` 收据（2244 → 2248）并重跑 `test_outsider_rerun`；
2. 补 `medxpert-reg-connector` 的 `fastmcp` 依赖声明；
3. 给零校验仓库补测试、给 13 件自检仓库升级成测试；
4. 把七件套与本报告推到远端（推送属写动作）。

## 八、写动作结果与读数变更（2026-11-26 16:00 后）

| # | 动作 | 结果 | 证据 |
|---|---|---|---|
| 1 | uibc-core 收据 | ✅ main 已更新 | 重生成 `2248 files / 3163aff2f57f / 4 steps passed`；commit `6cdde5468a` + `87738fe978`；本地 `test_outsider_rerun` 5 passed；远端 zipball `--check` exit 0 |
| 2 | fastmcp 依赖 | ✅ 无需改仓库（`pyproject` 早已声明 `fastmcp>=3.4,<5`） | 本机 fastmcp 4.2.0；`tests/selftest_stdio.py` exit 0（7 tools / 27 hubs / 15 sources） |
| 3 | LGD-Eval 镜像 | ✅ 已落地 | 解除归档 → 分支 → **PR #2** → squash merge `a22d1a68` → 恢复归档；远端 zipball `check-catalog` exit 0（15 条全索引） |
| 4 | 八件套与报告 | ✅ 已推送 | `third-party-rerun-kit` commit `9e95e481`（17 文件）+ `8a5db9e0`（补丁与执行记录）+ `71285acc`（远端复核补记） |

**读数变更（自检档，不计入 E5 合格）**：13 件仅自检中，`LGD-Eval/silent-failure-catalog` 由 fail 转为修复后通过，
家机口径 **7 ok / 6 fail**（原 6/7）；公司机同为 **7 ok / 6 fail**（原 5/8，另有一件环境差异）。
原始判 fail 的记录保留在 `e5_selfcheck.json` 的 `original_verdict` / `original_exit` / `original_tail` 字段，不改写历史。

**执行层 36/61 合格未变**：上述修复落在自检档与收据，不影响 61 件「有测试」的判定结果。

**还没做到的**：

- E2「无利益第三方」空位未补：执行者仍是持证人本人，这条不能靠多跑几轮解决。
- 180 件零校验、14 件 no_tests_collected、8 件 not_runnable 仍需各仓库 owner 补测试或修夹具。
- `third-party-rerun-kit` 与 `uibc-core` 均有并发写入源在活动（`uibc-core` main 在我提交后被推到 `1b861dbb`，
  收据仍匹配）；任何人重跑前必须重取 zipball，否则会拿旧树对不上。
