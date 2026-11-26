# 断言判定算法（E5 严格合格线的可复算规则）

外部审查要求"提供测试文件内断言的判定算法"。本文件就是算法本身，任何人可据它独立复算 34/2。

## 一、先定位"哪些文件算测试文件"

解包 zipball 后全树扫描，跳过 `.git`、`node_modules`、`venv`、`.venv`、`dist`、`build`、`__pycache__`、`.tox`，只看 `.py/.js/.mjs/.cjs/.ts`，命中任一条件即算：

- 路径位于 `*/tests/*` 下；
- 文件名以 `test_` 开头；
- 文件名以 `_test.py`、`.test.js`、`.spec.js`、`.test.mjs`、`.spec.mjs` 结尾；
- `conftest.py` 不算。

每件最多取 40 个文件，按路径序遍历，正文按行判定。

## 二、单行的四种判定

| 类别 | 规则 | 计法 |
|---|---|---|
| 平凡断言 | `assert True/False/None/1/0/""/'')`、`assertTrue(True)`、`assertFalse(False)` | 记 trivial，**不计强断言** |
| 强断言 | `assert <非平凡表达式>`；`assertEqual/assertTrue/assertFalse/assertIn/assertNotIn/assertRaises/assertIs/assertIsNot/assertGreater/assertLess/assertAlmostEqual/assertRegex`；`pytest.raises(`；`expect(...).to/.not`；`self.assert*`；Rust `assert!` | 记 strong |
| 状态比对 | 行内出现 `==` 或 `!=`，且该行不以 `if `、`while `、`elif `、`assert` 开头 | 记 cmp（弱证据） |
| 其他 | 注释行（`#`、`//`）直接跳过 | — |

判定顺序：先查平凡断言（命中即跳过本行，不重复计强断言），再查强断言，最后查状态比对。

## 三、件的合格判定

```
strict = passed >= 3  且  (strong >= 1  或  cmp >= 1)
thin   = 不满足上式（含 passed < 3、或测试文件内既无断言也无状态比对）
```

## 四、这套规则自身的两处边界（实测定出来，如实记）

### 1. `return s == "OK"` 算不算状态比对

`zhaoxinghua09-cell/evidence-anchor` 的 `tests/run_golden.py`（102 行）没有 `assert`，判定方式是 `return s == "OK"` 这类返回码比对。第一版规则把 `return ` 开头排除，该件被判 thin；修正后允许 `return` 参与 cmp，判 strict。

理由：golden 脚本的判定就是返回状态，排除 `return` 等于要求"用 pytest 的写法"，与"不限定测试框架"自相矛盾。本版采用修正后规则。

### 2. 有一行都不命中的"测试文件"

`zhaoxinghua09-cell/skill-improver` 的 `tests/run_golden.py`（135 行）**零 assert、零 `==`/`!=` 比对**，唯一的输出是打印。它 passed=9，但 9 条全是脚本自报。按本规则判 thin——这是规则正确工作的例子，不是误判。

同一件在家机上一轮判为 strict，原因是家机那版走了另一条文件定位路径（deep 的 `samples` 字段），定位到了别的文件。**这正说明：结果对"文件定位方式"敏感，所以算法必须公开、逐件样本必须留档。**

## 五、复算命令

```bash
# 公司机侧（全树定位 + 本规则）
python e5_assert_audit.py
# 输出 e5_20261125/e5_assert_audit_company.json：
#   summary.strict / summary.thin / 每件的 strong、trivial、cmp、files_scanned、samples
```

逐件记录里带 `samples`（最多 3 条真实断言行原文），第三方可任取一件核对"这条是不是它说的断言"。

## 六、已知局限（不外推）

- 静态正则只能证明"文件里有断言字符"，**不能证明断言覆盖了被测逻辑**。`assert x == x` 同样计 strong——要证后者需要变异测试（改实现看测试是否变红），本版未做。
- `assertEqual(a, b)` 中 a、b 若都是常量，语义上等于平凡断言，但静态无法区分，计入 strong。
- 因此本规则给的是"有断言证据"的下界，不是"测试有效性"的上界。
