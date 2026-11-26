# 跨操作系统复跑：Linux（无凭据通道）

## 一句话结论

**同一份源码树，在 Linux 上与 Windows 上指纹分毫不差（7/7 SAME）；读数 6/7 一致，唯一的差异件不是操作系统造成的，是它自己有三套入口。**

## 实测环境

- 云主机 Linux，Python 3.12.11，pytest 8.4.2，Node v22.23.4
- 传输通道改用 `codeload.github.com/<repo>/zip/<commit>`：**不需要任何 token**，公开仓库直接下
- 判定器仍是同一份 `e5_verify_all.py`（只替换传输层与路径，判定逻辑一字未改，保证可比）

这一条本身比读数更重要：**第三方复跑的门槛从"要一个只读 token"降到"一个 curl"**。

## 逐件结果

| 仓库 | 基线 | Linux 复跑 | 树指纹 | 入口 |
|---|---|---|---|---|
| `zhaoxinghua09-cell/lgd-skill-review` | 5 | 0（未识别） | SAME | `tests/selftest_endpoint_consistency.py` |
| `zhaoxinghua09-cell/wexp-check` | 37 | 37 | SAME | pytest |
| `stevenzhao07/regdoc-commons` | 52 | 52 | SAME | `tests/run.js`（node） |
| `stevenzhao07/doc-translate-keep-layout` | 40 | 40 | SAME | `tests/run_tests.py` |
| `zhaoxinghua09-cell/evidence-anchor` | 9 | 9 | SAME | `tests/run_golden.py` |
| `zhaoxinghua09-cell/claim-audit` | 9 | 9 | SAME | `tests/run_golden.py` |
| `zhaoxinghua09-cell/aps-conformance-suite` | 20 | 20 | SAME | pytest |

指纹 7/7 SAME、`tree_diff` 为空。注意 `regdoc-commons` 的 `run.js` 在 Linux 上照样跑出 52——入口规则跨平台有效。

## 唯一差异件：`lgd-skill-review` 有三套入口、三个读数

同一棵树（commit `7fe24c39c711`）在 Linux 上：

1. `pytest tests` → **`INTERNALERROR`，`no tests ran`**
2. `python3 tests/run_golden.py` → **4/5 PASS**（`T5-self-scores-100` 判 FAIL）
3. `python3 tests/selftest_endpoint_consistency.py` → `ENDPOINT-CONSISTENCY-SELFTEST: 8/8`
4. Windows 上同 commit 的 pytest → 5 条

根因已定位：`tests/test_endpoint_consistency.py` 在**模块顶层**执行 `sys.exit(0 if ok == len(results) else 1)`。pytest 在导入该模块时吃到 `SystemExit`，整个会话 `INTERNALERROR` 退出。这是仓库的反模式，不是我的判定器错——但它跨平台表现不同（Windows 侧收集成功），所以它成了"平台函数"。

我这边的判定器未识别 `4/5 PASS` 与 `8/8` 这两种无关键字格式，因此记 0。人工核实是 4/5。**记 0 与记 4 都不等于基线 5，这件在 Linux 上无法对到基线**，这是事实，不修饰。

## 三条可外传的结论

1. **源码层可复现性与 OS 无关**。指纹在 Linux 与 Windows 上逐字节相同（7/7）。要证伪只需改一个字符，前面已做过负控。
2. **读数层的差异多来自入口与反模式，不是 OS**。6/7 一致已经把 OS 洗清；那 1 件是三入口问题。
3. **读数元数据必须四件套**：OS、Python 版本、pytest 版本、Node 版本。少一项就是不可复算的读数。此前只记机器名，不够。

## 新增反模式清单（建议进 RUNBOOK）

- 测试文件**模块顶层**调用 `sys.exit()`：会让 pytest 直接 `INTERNALERROR`（Linux 实测），应放进 `if __name__ == "__main__":`
- `tests/` 下同时存在 `run*.py`、`run*.js`、`test_*.py`：三套读数（8/4/5 这种），必须指定唯一入口
- 自执行脚本用 `8/8`、`4/5 通过` 这类无 `PASS` 关键字的格式：外部判定器无法通用解析

## 局限（不省）

- 只跑 7 件，不是 36 件全量；`uibc-core`（158 条）等重件未在 Linux 上跑。
- 云主机无推送凭据，原始读数 `e5_verify_linux7.json` 留在云主机 `/home/user/e5/`，**未上传远端**。本报告只用实测数字，不含推断。
- Linux 侧判定器对 `4/5 PASS`、`8/8` 两种格式未做识别，记 0；这是判定器的已知缺口，未在本轮修补（补了会改变全量读数，需另开一轮并重跑基线）。
- 仍只覆盖"严格合格 + 薄证据"层。

## 与竞品的关系

Reproducible Builds 关心"同一源码在不同环境构建出同一产物"；SLSA 关心"产物出自谁"；Scorecard 关心"仓库配置是否达标"。本套关心的是**"读数能不能被别人在他自己的机器上复现"**，并且现在多了一层：**跨操作系统时，源码树是否仍然逐字节一致**。

差在哪仍需明说：我没有做构建产物字节一致，也没有做依赖锁定的环境复现（只固定了 commit，没固定 pip 依赖版本）。
