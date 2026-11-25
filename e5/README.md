# E5 · Outsider full-suite runner

把「一个账号名下到底有多少仓库能被外人跑出读数」变成可复跑的四档统计，而不是抽样表态。

## 四档口径

| 档 | 判定 | 是否计入 E5 合格 |
|---|---|---|
| 有测试 | 树里存在 pytest / 自研 runner（`tests/run_*.py`、`tests/run.js`）/ JS `test` 脚本 / 可自执行测试脚本 | 是（需真跑通） |
| 仅自检 | 只有 `check_links.py`、`verify_chain.py` 一类完整性脚本 | **否**：链接没坏不等于被测代码正确 |
| 无校验 | 全树零校验文件 | 否 |
| 缺失/错误 | 无法探测 | 否 |

「有测试」的判定必须扫**全树**，不能只看顶层：测试放在 `service/`、`tools/`、`skills/*/tests/`、`audit/*/` 的仓库会被顶层枚举漏掉。

## 八件套执行顺序

```bash
python e5_build_manifest.py      # 1. users/{owner}/repos 翻页到底，清单 + commit 锚定
python e5_probe.py               # 2. 顶层结构探测（入口/测试/README）
python e5_deep.py --all          # 3. git/trees/<sha>?recursive=1 全树扫描，三档
python e5_deep_merge.py          # 4. 深层命中升格 + 仅自检标记
python e5_run.py                 # 5. zipball 解包真跑（pytest / 自研 runner / npm test / node --test）
python e5_selfcheck.py           # 6. 仅自检那档真跑（不计合格）
python e5_merge.py               # 7. 回写 manifest
python e5_board.py               # 8. 生成看板 HTML（零外链）
```

## 复跑前置

- Python 3.9+、`pytest`；JS 仓库需要 Node。
- 一个只读 GitHub token（`repo` scope 足够，只读不写）：清单与全树扫描走 `api.github.com`，限流 4000/h（认证后）。
- 不需要 `github.com` 的 git 通道：zipball 与 tree 都走 API，因此在只放通 `api.github.com` 的网络里也能跑完。
- `e5_run.py` 每件仓库解包到临时目录，跑完即弃；**不 clone、不 push、不改被测仓库**。

## 最新读数（2026-11-26）

- 分母：三账号 254 件（zhaoxinghua09-cell 193 / stevenzhao07 36 / LGD-Eval 25）。
- 四档：61 有测试（48 顶层 + 13 深层）/ 13 仅自检 / 180 无校验 / 0 缺失。
- 执行：61/61 已跑；**36 合格**；累计 3971 passed（公司机）、3862 passed（家机）。
- 自检档：公司机 5 ok / 8 fail；家机 6 ok / 7 fail。
- 两机构成只差 1 件归因；同一 commit 同一 zipball，两机失败项不同 —— 这是「外人复跑必须多环境」的直接证据。

## 已知限制（必须写在读数旁边，不能省）

- **archived 仓库不可写**：`LGD-Eval/silent-failure-catalog` 已归档，自检 fail 的修复只能本地验证（`check-catalog` 已 PASS，15 条），远端需要 unarchive 才能落地。
- 链接类自检依赖外网：网络受限的机器会把 `check_links` 判成 fail（如 `LGD-Eval/awesome-agent-skills-1`，公司机 fail / 家机 ok）。
- 宿主 pytest 配置可能干扰：树上存在会 `sys.exit(0)` 的脚本时，裸 `pytest` 会被打断，须显式 `pytest tests`。
- 「仅自检通过」永远不计合格 —— 否则等于用「文件都在」冒充「代码正确」。

## 与竞品口径的关系

- OpenSSF Scorecard `CI-Tests` 只读 GitHub `CheckRuns`/`Statuses` 的历史痕迹，**不本地跑**。
- SLSA `verifying-artifacts` 验的是 provenance 签名与 builder 绑定，判「产物出自谁」，**不判外人能否跑通**。
- 本工具补的正是这两者都不覆盖的一层：在无 `.git`、无凭证的干净副本里，由外部机器重跑并留读数。三者并列，不互相冒充。
