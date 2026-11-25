# E5 四项写动作执行记录（2026-11-26）

本机：赵兴华的台式机（client:582478:2751453223723051）。GitHub 通道结论：`github.com` 的
git over HTTPS 被重置（`Recv failure: Connection was reset`），**只有 `api.github.com` 可达**，
因此全部写入走 REST API（Contents API / Git Data API），未使用 git 客户端。

---

## 一、uibc-core 收据 — 已修复并推送到 main

**做法**：取当前 commit `7ff56ab` 的 zipball，解包为无 `.git` 的干净树，运行仓库自带的
`tools/outsider_rerun.py` 重新生成收据（它会把 gate / parity / demo / 两个测试文件四步重跑一遍）。

**结果**：

```
OUTSIDER OK: receipt matches this tree (2248 files, 3163aff2f57f), 4 steps passed
```

旧值是 `files_hashed = 2244`，新值是 `2248` —— 树里后来多了 4 个文件，收据没跟着更新，
`test_receipt_matches_this_tree` 因此报 `FILE COUNT MOVED`。

**已提交**（`zhaoxinghua09-cell/uibc-core`，branch `main`）：

| 文件 | commit |
|---|---|
| `docs/outsider-rerun-receipt.json` | `6cdde5468a` |
| `docs/OUTSIDER-RERUN.md` | `87738fe978` |

**本地复核**：

```
$ python -m pytest tests/test_outsider_rerun.py -q
5 passed in 17.21s
```

5 项含负控（改一个字节即失配）与「副本无 .git」检查，全部通过。

---

## 二、fastmcp 依赖 — 结论是「早已声明」，缺的是环境而非清单

`medxpert-reg-connector` 的 `pyproject.toml` 已写 `dependencies = ["fastmcp>=3.4,<5"]`，
`requirements.txt` 也列了 `fastmcp`。E5 里报 `ModuleNotFoundError` 是执行环境缺包，
不是仓库漏声明 —— 所以**不改仓库**，改为验证声明是否真的够用。

**验证**：

- 本机 fastmcp 版本 `4.2.0`，落在 `>=3.4,<5` 区间。
- `import medxpert_reg_connector.server` → `IMPORT OK`。
- `python tests/selftest_stdio.py` → `exit 0`，真跑了一次 MCP stdio 握手：

```
[ok] tools (7): list_hubs, search_regulation, get_hub, ask_classification, kb_freshness, reg_delta, kb_sources
[ok] readOnlyHint declared on 7/7 tools
[ok] all input params documented
[ok] list_hubs -> 27 hubs
[ok] kb_sources -> 15 official sources
[PASS] MCP contract self-test green
```

注：`pytest tests` 在该仓库返回 exit 5（`no tests ran`），因为 `tests/` 下只有
`selftest_stdio.py` 这个自执行脚本，不是 pytest 用例 —— 这正是不该用「pytest 收集数量」
判可运行性的例子。

**附带发现（独立缺陷，非本次范围）**：`kb_freshness` 报 `hubs 27 / overdue 27`，
知识库全部过期，是数据时效问题，不是代码问题。

---

## 三、LGD-Eval/silent-failure-catalog — 根因已修、本地全绿，但远端被「归档」锁死

**定位**：`check-catalog.py` 只允许 `docs/where-to-find-us.md` 与 `docs/start-here.md`
放 outbound self-link，而该仓库 `README.md` 第 1 行带 `https://zhaoxinghua09-cell.github.io/lgd-hub/`。

**修复后本地自检**：

```
entries: 15 / ids: SF-001 .. SF-015
PASS — every required section present, every id indexed, every link resolves.
exit 0
```

**为什么没提交**：该仓库 `archived: true`。归档仓库对 Contents API PUT 与 `git push`
一律返回 **403**，与 token 权限无关（用 LGD-Eval 自己的 token 也是 403）。
补丁与决策说明已落到 `third-party-rerun-kit/e5/patches/`。

**没有整树覆盖**：两版已分叉 —— steven 版 14 条（有 `CLAUDE.md`/`module.json`），
LGD-Eval 版 15 条（有 `SF-015-stale-reference-rot.md`、`release-attestation.yml`），
84 个文件里 13 个内容不同。覆盖会丢条目，所以只修不一致点。

**待 owner 决策**：unarchive 后套补丁，或明确冻结该版、只在 steven 版维护。

---

## 四、八件套 + 报告 — 已推到 `third-party-rerun-kit`（一次提交）

commit **`9e95e481f943bd29ab7dd3ae512a00516c6afef2`**，17 个文件：

```
e5/README.md                                复跑说明 + 四档口径 + 已知限制
e5/e5_build_manifest.py … e5/e5_board.py    八件套（按执行顺序编号）
e5/readouts/e5_structural.json              254 件结构层
e5/readouts/e5_deep_20261125.json           193 件全树三档
e5/readouts/e5_runner.json                  61 件执行层
e5/readouts/e5_selfcheck.json               13 件自检档
e5/readouts/artifact_manifest_20261125.json 254 件清单（probed=254 / pending=0）
e5/reports/E5_four_tier_report_20261126.md
e5/reports/E5_two_box_comparison_20261126.md
e5/board/E5_outsider_board_20261126.html    看板，零外链
```

选这个仓库的理由：它本来就是「外人复跑包」，未归档、可写、已有 `README.md` 与 `evidence/`，
八件套放进去语义最贴，不必新建仓库。

---

## 四项状态汇总

| # | 动作 | 状态 | 证据 |
|---|---|---|---|
| 1 | 修 uibc-core 收据 | ✅ 已推送 main | `6cdde5468a` / `87738fe978`；本地 5 passed |
| 2 | 补 fastmcp 依赖 | ✅ 无需改仓库，已验证可用 | fastmcp 4.2.0；selftest exit 0 |
| 3 | 同步 LGD-Eval 镜像 | ⚠️ 本地已修到 PASS，远端 403（仓库已归档） | 补丁在 `e5/patches/` |
| 4 | 推八件套与报告 | ✅ 已推送 | `9e95e481`，17 文件 |

唯一未落地的一步不是技术问题，是「归档仓库不可写」这一平台事实；
要落到远端，只需一次 unarchive 决策。

## 仍然不能声称的部分

- E5 的执行者仍是持有凭证的本人，不是无利益第三方 → E2 仍不是闭环，多跑几轮也不会变。
- 36/61 合格的结论未变；`silent-failure-catalog` 那条仍计在「自检 fail」档，未因本地修复而改分。
