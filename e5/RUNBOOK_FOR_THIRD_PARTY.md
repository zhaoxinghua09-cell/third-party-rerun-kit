# 第三方复跑执行单（E5，给没有利益关系的人）

你不必相信这份读数。下面是可以照着敲的命令，跑完你自己会有一份 json。
**如果你跑出的数字和 `e5/readouts/` 里的不一样，那才是重点——请把你那份留在自己机器上，并告诉我们差在哪。**

## 0. 你要准备什么

- Python 3.9+，`pip install pytest`（只跑结构层与清单层不需要 pytest）
- 可选：Node（只影响 8 个 JS 仓库的 `npm test`/`node --test` 判定）
- 一个**只读** GitHub token（classic 的 `repo` 或 fine-grained 的 Contents:Read 即可）。
  没有 token 也能跑，但匿名限流 60 次/小时，254 个仓库扫不完。
- 不需要 `git` 客户端，不需要 `github.com` 的 443 直连——我们全程走 `api.github.com`。
  这一点很重要：**在网络受限的机器上，这套照样能跑完**，这正是它和"看 CI 绿不绿"的区别。

## 1. 取工具

```bash
git clone https://github.com/zhaoxinghua09-cell/third-party-rerun-kit
cd third-party-rerun-kit/e5
export GH_TOKEN=<你的只读 token>      # Windows: $env:GH_TOKEN="..."
python -m pip install pytest
```

## 2. 跑三层（按顺序，前一层喂后一层）

```bash
python e5_build_manifest.py      # 1) 枚举三账号全部仓库 -> artifact_manifest*.json
python e5_probe.py               # 2) 顶层结构：有没有入口
python e5_deep.py --all          # 3) 全树扫描：三档（有测试 / 仅自检 / 零校验）
python e5_deep_merge.py          # 4) 把深层命中升格，标出仅自检
python e5_run.py                 # 5) 真跑（zipball 解包 -> pytest / 自研 runner / npm）
python e5_selfcheck.py           # 6) 仅自检那档单独跑（不计合格）
python e5_merge.py               # 7) 回写
python e5_board.py               # 8) 出看板 HTML
```

时间预算：2) + 3) 约 2 分钟；5) 取决于机器，公司机约 40 分钟、家机约 50 分钟。

## 3. 怎么判"我们没吹"

对照我们公开的读数（`e5/readouts/`）：

| 你应该看到 | 我们的数 | 若你的不符，说明 |
|---|---|---|
| 入册仓库数 | 254（193/36/25） | token 看到的仓库范围不同（权限/组织成员身份差异） |
| 有测试 | 61 | 全树扫描口径不同（是否递归、是否排除 vendor） |
| 仅自检 | 13 | 同上 |
| 执行 61 件、合格 36 | 61/61、36 | 环境差异（Windows 无 POSIX symlink、依赖缺失） |
| 累计 passed | 公司机 3971 / 家机 3862 | 允许不同；两机本来就不同，我们没抹平 |

**关键一条**：合格定义是「passed>0 且 failed=0 且 errors=0 且 exit=0」。
即使某仓库有 2000 条测试通过、只挂 1 条，也不算合格——`uibc-core` 就是这种，它被记成 partial，不是 pass。

## 4. 三个已知坑（别人踩过，提前说）

1. **裸 `pytest` 会被打断**：某些仓库树里有会 `sys.exit(0)` 的脚本，必须显式 `pytest tests` 或指定文件。
2. **链接类自检依赖外网**：`check_links.py` 在断网机器上会假失败（`LGD-Eval/awesome-agent-skills-1` 就是这样）。
3. **收据与树计数口径**：`uibc-core` 的 `tools/outsider_rerun.py --check` 要的是"缺 `.git` 的干净树"；在 git clone 出来的工作区跑会因 `.git` 与缓存文件而计数不同，请用 zipball 解包后再跑。

## 5. 你跑完之后

- 保留你自己的 `e5_structural.json` / `e5_runner.json` / `e5_selfcheck.json`；
- 记下你跑的那次 commit（`git rev-parse HEAD`）；
- 如果差异来自环境而非仓库，请在结果里注明机器与 OS——**两台机器数字不同不是 bug，是这套方法要求的**；
- 我们不会要求你"跑出和我们一样的数"，只要求你把你的数留着，别改。

## 6. 这套东西不做什么

- 不验证产物签名（那是 SLSA 的活）；
- 不做更新框架的角色与阈值（那是 TUF 的活）；
- 不建公开可审计日志（那是 RFC 6962 CT 的活）；
- 不做内容凭证（那是 C2PA 的活）。

它只回答一件事：**这个仓库，一个没有凭证、没有 `.git`、没有作者机器状态的外人，能不能把它跑出真实读数。**
