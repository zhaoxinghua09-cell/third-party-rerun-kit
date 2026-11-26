# 变异检查：断言存在 ≠ 断言有效（A 档 12 件）

上一轮解决的是「测试里有没有断言」。这一轮解决下一个问题：**断言真的会抓到 bug，还是写在那里热闹。**

方法是变异测试（mutation testing）：往实现代码里注入一处语义改变，跑测试。测试变红（fail/error）＝这处逻辑被覆盖，记 KILLED；测试照样绿＝没抓到，记 SURVIVED。

## 一、做法（可复算）

- 对象：严格合格中 `evidence_tier=A` 的 12 件（passed ≥ 20）。
- 每件**只注入 1 个变异点**，在临时解包副本里改，不碰仓库、不推远端，跑完即删。
- 变异算子按优先级取第一个可用：
  1. `Compare(Eq)` → `NotEq`（把相等判断翻成不等）；
  2. `Return(Constant int)` → 常量 +1；
  3. `BoolOp And` ↔ `Or`。
- 实现文件排除 `tests/`、`docs/`、`examples/`、`reproductions/`、`archive/`、`legacy/`（历史复现脚本不属于被测代码，第一版没排除时 wexp-check 的变异落在 `reproductions/...` 上，已修正重跑）。
- 测试入口与 E5 主判定一致：`pytest` 全部测试文件，`--maxfail=5`。

## 二、读数（2026-11-26 08:29，公司机）

| 仓库 | 变异点 | 结果 |
|---|---|---|
| zhaoxinghua09-cell/lgd-xverify | `lgd_ed25519.py` Eq→NotEq 第 31 行 | **KILLED** |
| zhaoxinghua09-cell/wexp-check | `scripts/compare_corpora.py` Eq→NotEq 第 23 行 | SURVIVED |
| zhaoxinghua09-cell/medxpert-ortho-mcp | `medxpert_ortho/core.py` Eq→NotEq 第 110 行 | **KILLED** |
| stevenzhao07/doc-translate-keep-layout | `scripts/glossary_build.py` Eq→NotEq 第 166 行 | **KILLED** |
| stevenzhao07/regdoc-commons | 12 个实现文件无可变异节点 | SKIP |
| zhaoxinghua09-cell/summarize-pro | `demo/run_demo.py` Eq→NotEq 第 66 行 | **KILLED** |
| zhaoxinghua09-cell/aps-conformance-suite | `candidates/aeoess-oauth-actor-profile/check.py` 第 41 行 | **KILLED** |
| stevenzhao07/uibc-core | `adapters/a2a/server.py` Eq→NotEq 第 59 行 | **KILLED** |
| LGD-Eval/uibc-core | 同上（镜像同源） | **KILLED** |
| zhaoxinghua09-cell/skillgate | `alert.py` Eq→NotEq 第 65 行 | SURVIVED |
| stevenzhao07/aitb | `src/aitb/adapters.py` Eq→NotEq 第 92 行 | **KILLED** |
| LGD-Eval/awesome-claude-code | `generate_readme.py` Eq→NotEq 第 154 行 | **KILLED** |

**变异得分：9 / 11 = 0.818**（SKIP 1 件不计入分母）。

## 三、两件 SURVIVED 到底说明什么

- `wexp-check`：变异在 `scripts/compare_corpora.py` 第 23 行。换成 `reproductions/` 里的点也一样绿——说明这件的测试覆盖的是核心数据模块，没覆盖 `scripts/` 下的 CLI 工具。**结论是「这个脚本没有测试」，不是「这件的断言是假的」。**
- `skillgate`：变异在 `alert.py` 第 65 行，测试未变红。同类推断：告警分支的相等判断缺用例。

两者都是「局部未覆盖」，就地暴露给自己，不掩盖。要救需要给对应模块补用例，本轮不代写。

## 四、SKIP 1 件

`stevenzhao07/regdoc-commons`：12 个候选实现文件里没有任何 `Compare(Eq)` 或 `Return(常量)` 节点可供机械替换。不是失败，是这套算子不适用；要覆盖需人工设计语义变异（如删掉一段校验、改一个正则）。

## 五、局限（必须与读数一起出现）

1. **1 个变异点 ≠ 覆盖率。** 得分 0.818 只能说明「抽样点里 9 个被抓住」，不能推成「82% 的代码被测试覆盖」。
2. **命中位置由文件遍历顺序决定**，可能落在边缘函数上；落在哪就报哪，不做挑选美化。
3. **死代码命中会被记成 SURVIVED**（本该如此：死代码本就没人测）。
4. 每个变异算子只改一处，等价于「最弱检验」；真正的变异测试会给每件生成几十个变异体求整体得分，成本高一个量级，本轮不做。

## 六、这一轮往前挪了多少

| 层次 | 上一轮 | 这一轮 |
|---|---|---|
| 能不能跑 | 61/61 实跑 | 不变 |
| 测试里有没有断言 | 33 件有（薄证据 3 件剔除） | 不变 |
| **断言会不会抓到 bug** | 未测 | **11 件可测中 9 件 KILLED（0.818）** |

第三层是目前唯一能证明「测试不是摆设」的机械证据，也是外部审查 B 问「断言是否有意义」的直接回答。
