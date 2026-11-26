# 一键复跑器：一条命令，让第三方自己比对读数

前面几轮都在证明「我们有读数」。这一轮证明的是**「别人拿到一条命令就能验这份读数」**——这是 E2 最短的路径，也是外部审查 D 问「最省力证伪」的正解：让人自己跑。

## 一、怎么用

```bash
pip install pytest
export GH_TOKEN=<只读 repo scope 的 token>      # Windows: $env:GH_TOKEN="..."
python e5_verify_all.py              # 默认抽 8 件（A2/B3/C2/薄1）
python e5_verify_all.py --n 16       # 多抽
python e5_verify_all.py --repos owner/a owner/b
```

它做的事：按证据强度分层抽件 → 从 commit 下载 zipball（无 `.git`、无凭证）→ 跑测试 → 与 `readouts/e5_runner.json` 的基线读数逐件比对 → 输出 `MATCH / DIFF` 与匹配率，退出码 0 = 全一致，1 = 有差异。

不需要本机已有的 `e5_20261125/` 大文件，只要仓库里这份脚本与读数。

## 二、实测：三版迭代才到 8/8

| 版本 | 做法 | 结果 |
|---|---|---|
| 第一版 | `pytest <测试文件列表>` | **3/8 MATCH**，5 件 `no tests ran`（exit 3/5） |
| 第二版 | 收不到用例时回落自执行脚本（`tests/run*.py`） | **6/8**，`lgd-xverify`/`lgd-skeleton` 仍 0 passed |
| 第三版 | 有 `tests/` 目录就 `pytest tests`（而非文件列表） | **8/8 MATCH，匹配率 1.0** |

8 件实测（2026-11-26 08:41，公司机，Python 3.13.18 / win32）：

| 仓库 | 档 | 基线 passed | 本机 passed | 结论 |
|---|---|---|---|---|
| lgd-xverify | A | 28 | 28 | MATCH |
| wexp-check | A | 37 | 37 | MATCH |
| lgd-skeleton | B | 14 | 14 | MATCH |
| uibc-iverify | B | 10 | 10 | MATCH |
| debug-pro | B | 10 | 10 | MATCH |
| lgd-skill-review | C | 5 | 5 | MATCH |
| evaluation-evidence | C | 5 | 5 | MATCH |
| fgtida-paris-input-2026 | 薄 | 1 | 1 | MATCH |

## 三、两次 DIFF 教给我们的东西

**第一版 5 件 DIFF，全部同一个原因：`no tests ran`。** 但仓库里的 `tests/` 明明有文件——问题在于我传的是"文件路径列表"，pytest 进不到那些文件所依赖的上下文（`conftest.py`、相对导入、包内路径），于是收集为空。

**这是本轮最重要的一条事实**：同一 commit、同一 zipball、同一台机器，**仅仅因为传的是目录还是文件列表，28 条通过就变成 0 条**。

上一轮外部审查 D 问说「最省力的证伪路径是换环境跑」，实测下来更省力的是**换入口写法**。所以：
- 把入口规则写进脚本（`tests/` 目录优先，收不到再回落自执行脚本）；
- `RUNBOOK_FOR_THIRD_PARTY.md` 里已有「裸 pytest 会被 `sys.exit(0)` 打断，须显式 `pytest tests`」，这一条现在有了机器可执行的版本。

## 四、局限

1. 默认只抽 8 件（≈24%），不是全量 33 件；`--n 33` 可以跑全量，代价是时间。
2. 同机同环境验证，跨机仍会有依赖/平台差异（见 `two_machine_failure_top3`）。
3. 它比对的是「passed 条数是否与基线一致」，不校验测试内容是否被篡改——后者要哈希/收据，不在本脚本范围。

## 五、它对应的门禁位置

- 对 **E5**：证明读数可被外人原样复现（数据层）；
- 对 **E2**：它是外人实跑的技术部分，但 `who` 必须是真人非协作者才算通过——脚本不能替人签这个名；
- 对 **E1**：无关。

一句话：这条命令把「你信不信我的数」变成「你自己跑一遍看」。
