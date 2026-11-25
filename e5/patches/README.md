# LGD-Eval/silent-failure-catalog — 归档仓库的修复包

## 为什么这里只有补丁，没有提交

该仓库 `archived: true`。GitHub 对归档仓库的任何写入（Contents API PUT、`git push`）一律 403，
无论 token 有 `repo` 权限还是仓库管理员。这是平台硬约束，不是权限没配好。

因此修复只能：本地验证 → 留补丁 → 等 unarchive 后套用。

## 失败根因（可复现）

`tools/check-catalog.py` 的规则是：只有 `docs/where-to-find-us.md` 与 `docs/start-here.md` 两个入口页
可以放 outbound self-link，其他文件一律不许。而 `README.md` 第 1 行带了一句：

```
portal: https://zhaoxinghua09-cell.github.io/lgd-hub/
```

于是自检报：

```
🔴 README.md  line 1: outbound link to the account's static-hosting host ('https://zhaoxinghua09-cell.github.io/')
FAIL — a required item is absent or inconsistent.
```

## 本地验证（已跑）

改第 1 行为指向入口页的相对链接后：

```
$ python tools/check-catalog.py
  entries: 15
  ids    : SF-001 ... SF-014, SF-015
PASS — every required section present, every id indexed, every link resolves.
exit 0
```

## 不采用「整树覆盖」的原因

两版不是镜像，是两个分叉：

| | stevenzhao07 版 | LGD-Eval 版 |
|---|---|---|
| 文件数 | 84 | 84 |
| 条目数 | 14（SF-001..SF-014） | 15（多了 SF-015-stale-reference-rot） |
| 专属文件 | `CLAUDE.md`、`module.json`、`codeql.yml`、`scorecard.yml` | `release-attestation.yml`、`security-baseline.yml`、`codeql-sast.yml`、`failures/SF-015-*.md` |
| 自检 | PASS | FAIL（即本补丁修的那一条） |

共有文件里 13 个内容不同。用 steven 版覆盖 LGD-Eval 版会丢掉 SF-015 与发布证明工作流；
正确做法是修 LGD-Eval 版自己的不一致点，而不是抹平差异。

## 落地路径（二选一，需 owner 决策）

1. **unarchive 后套补丁**：`gh api -X PATCH repos/LGD-Eval/silent-failure-catalog -f archived=false`，
   再按 `lgd-eval-silent-failure-catalog-readme.patch` 更新 README.md，重跑自检确认 PASS。
2. **冻结 LGD-Eval 版**：把它作为历史快照，只在 stevenzhao07 版继续维护，
   并在本文件与 E5 读数里标注「LGD-Eval 版自检 fail 属归档只读，不计入待修」。
