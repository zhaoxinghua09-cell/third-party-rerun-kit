# uibc-core 版本 DRIFT 说明（外部审查条件 3）

外部审查要求「修复 uibc-core 版本差异文档，注明 DRIFT 原因与时间」。**不清除 DRIFT，只把事实写清楚**——清除需要用户本人在 Zenodo 建新版本，我不擅自改登记册。

## 一、三处对不上的版本号

| 位置 | 版本 | 来源 | 时间锚点 |
|---|---|---|---|
| 站位登记册 `standing.json` | 0.2.1 | 登记时写入 | 登记当日 |
| 仓库 `pyproject.toml` / 包元数据 | 0.5.0 | 仓库 main 当前值 | 随 commit `7ff56ab` 一并可见 |
| `citation.cff` | 0.4.2 | 引用文件当前值 | 同上 |

站位脚本 `standing_check.py` 的判定是 `uibc-core` **DRIFT**，整体 `verdict = PROBLEMS`，`can_stake_new = false`。

## 二、为什么不能就地改

- `standing.json` 的 `drift_note` 原文限定：三处统一需**用户本人在 Zenodo 建新 version**，不得擅自改登记版本号。
- 版本号是 DOI 绑定的对象。只改文本不改 DOI，等于把「已归档的 0.2.1」和「未归档的 0.5.0」缝在一起，比 DRIFT 本身更坏。
- 因此本项处置是「记录 + 禁止对外声称」，不是「修复」。

## 三、对外必须遵守的措辞约束

`honest_note` 已写死：**对外不得写成「已按 0.5.0 发布并已归档」**。任何材料引用 uibc-core 时，只能写「仓库 main 当前版本 0.5.0，归档版本 0.2.1，二者未统一」，或干脆不引用版本号。

## 四、解除条件（按顺序）

1. 用户在 Zenodo 创建 uibc-core 新 version，绑定当前 main 的 commit 与文件集；
2. 拿到新 DOI 后，同步更新 `citation.cff` 与 `pyproject.toml` 到同一版本号；
3. 重跑 `D:\Workbuddy\发布总账\站位工具\standing_check.py`，确认 `uibc-core` 不再是 DRIFT；
4. 只有第 3 步通过后，才允许对新版本做任何「已归档」表述。

在此之前，E5 中 uibc-core 的读数（2092 passed / 1 failed，且收据已由 `outsider_rerun.py` 重生成并远端复核 exit 0）只用于证明「外部可复跑」，不用于任何发布声明。
