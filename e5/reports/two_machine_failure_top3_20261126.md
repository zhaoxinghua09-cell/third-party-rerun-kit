# 两机失败差异：TOP3 根本原因

外部审查要求「声明两机失败差异的 TOP3 根本原因」。两台机器跑的是**同一 commit、同一 zipball**（清单逐件锚定 SHA），却给出不同读数——这既是「外人复跑必须多环境」的证据，也说明单机读数不能当绝对值。

## 一、差异总览

| 指标 | 公司机（DESKTOP-IGJBTUB / SZYL） | 家机（赵兴华的台式机 / Administrator） |
|---|---|---|
| 61 件执行结论 | pass 36 / partial 3 / 空收集 13 / 跑不起来 9 | pass 36 / partial 3 / 空收集 14 / 跑不起来 8 |
| 累计 passed | 3971 | 3862 |
| 严格合格（有断言证据） | 33 | 34（含 1 件本轮改判薄，见下） |

## 二、逐件差异（4 处，其余 57 件一致）

| 仓库 | 公司机 | 家机 |
|---|---|---|
| zhaoxinghua09-cell/agent-control-standard | 901 passed / 17 failed | 794 passed / 20 failed |
| zhaoxinghua09-cell/uibc-core | 2092 passed / 1 failed | 2090 passed / 2 failed |
| zhaoxinghua09-cell/agent-memory-service | not_runnable（4 errors） | no_tests_collected |
| zhaoxinghua09-cell/medxpert-reg-connector | not_runnable（`ModuleNotFoundError: fastmcp`） | not_runnable（运行到 `transport 'stdio'` 才停） |

## 三、TOP3 根因

### 根因 1：依赖可导入性差异（影响 2 件）

`medxpert-reg-connector` 在公司机连 import 都过不去（`No module named 'fastmcp'`），家机则已跨过导入、跑到 MCP transport 初始化。`agent-memory-service` 同源：公司机 pytest 能收集到用例但 4 个 error（可导入性/夹具初始化失败），家机直接收集 0 条。

同一份 `pyproject.toml` 声明了 `fastmcp>=3.4,<5`，缺的不是清单而是**机器上的实际环境**。这就是外部审查条件 4 要求「依赖预装清单」的现实依据——不写清楚，外人复跑得到的是环境错误，不是代码结论。

### 根因 2：测试用例对平台/网络/时序过敏（影响 2 件，且改变通过条数）

`agent-control-standard` 两机通过数差 **107 条**、失败数差 3 条；`uibc-core` 差 2 条通过、1 条失败。两机跑的字节流完全相同。

这些差集中的用例集中在 symlink 语义（Windows 无 POSIX symlink）、站点脚本白名单（依赖外网）、并发/时序断言。**它们不是逻辑失败，是环境函数**。含义很明确：任何「N 条通过」的读数必须标注机器与平台，跨机比较只能看「两机都过」的子集。

### 根因 3：收集与入口判定差异（影响 2 件）

`no_tests_collected`（no tests ran）与 `not_runnable`（errors）在同 zipball 上互换，来自两处：宿主 pytest 配置（家机存在会让裸 `pytest` 提前 `sys.exit(0)` 的脚本）、以及 fallback 入口链的取用顺序。判定器已把实际入口写入 `fallback_entry`，但**两机读同一件时可能选用不同入口**——这是判定器需要继续收紧的地方，不是仓库的问题。

## 四、由此确定的口径（写死，不再动摇）

1. **对外的合格数一律取两机交集**：36 件原始合格两机一致，严格合格取交集 **33**。`skill-improver` 家机曾判 strict、公司机全树定位后判薄（`tests/run_golden.py` 135 行零断言），人工实核支持公司机判定，故从合格中剔除。
2. **单机读数只报「本机环境 + 本机结果」**，不写成仓库属性。
3. **pass 数不跨机加总**；3971 与 3862 各自成立，作差没有意义。
4. 依赖预装清单、入口假设、平台差异三项，必须与读数同页出现。
