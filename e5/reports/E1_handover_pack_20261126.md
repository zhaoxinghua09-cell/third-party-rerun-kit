# E1 交接包：把「外部 AI 审查」做成别人照抄即过

## 一、先纠正一件事：上一轮那个不是 E1

我在公司机用自己持有的 SiliconFlow key 调 DeepSeek-V3 做了完整审查（判决 CONDITIONAL PASS，五条件闭环）。按 v9 标准 `external_gate.py` 的判据，这条记录 `same_operator = true`（同一 operator 调用、同一台机器），属 **E1-P**，**不计入 E1**。

实测门禁：

```
python external_gate.py --all
→ SUMMARY: 36 条，PASS 0，REFUSE 36
→ 每条原因都是「E1 缺证据（missing file 外部门禁/external_ai/<id>.json）；E2 缺证据」
```

所以 E1 仍然是 FAIL，只是从「什么都没做」变成了「做了 E1-P，E1 仍缺」。上一轮表述里的「E1 已过」应读作「E1-P 已取得，E1 未过」。

## 二、E1 差什么（`check_e1` 的六个字段，缺一即拒）

| 字段 | 判据 | 谁能给 |
|---|---|---|
| `independent` | 必须 `true` | 不是本人评本人 |
| `vendor` + `model` | 都要有值 | 填写服务商与模型名 |
| `same_operator` | **不能是 `true`** | 必须换人持自己的凭证调用 |
| `reproducible_cmd` | 非空 | 能复跑的具体命令 |
| `artifacts` | ≥1 个且路径存在 | 原始响应的落盘副本 |
| `verdict` | `pass` / `fail`；`fail` 直接判不得发布 | 审查方的结论 |

六个字段里，只有 `same_operator` 是本人无论如何都无法满足的——它要求**另一个人**用自己的凭证调到同一个模型。这就是 E1 一直缺位的真实原因。

## 三、交接给他人的操作（10 分钟）

### 1. 准备

- 自己的 API key（任何模型服务商即可，需与 S1 项不同供应商）；
- 一台不是本人的机器（同一台也行，但 `same_operator` 必须如实填 `false` 才成立——如果确实是本人操作，就必须填 `true`，那就不算 E1）。

### 2. 提示词（原样复制，勿改）

系统：

```
你是独立的第三方审查员，任务是审计一份自称"外人可复跑"的代码门禁报告，目标是找出它站不住的地方，而不是替它背书。你与被审方无利益关系。只根据下面的材料判断，不要假设材料之外还有未写出的证据。
```

用户：

```
被审对象：一个名为 E5 的门禁，声称把三个 GitHub 账号下全部 254 个仓库按"外人能否实跑"分成四档并给出合格读数。

材料（全部来自被审方自述）：
1) 入册 254（193/36/25），清单从 users/{owner}/repos 翻页到底，每件锚定 commit。
2) 四档：61 件有测试（48 顶层 + 13 全树深层）、13 件仅自检脚本、180 件全树零校验。
3) 执行：61/61 全部下载 zipball、无 .git、无凭证，实跑 pytests/自研 runner/npm；判定=passed>0 且 failed=0 且 errors=0 且 exit=0 → 36 件合格；两台机器分别跑，累计通过 3971（公司机）/3862（家机）。
4) 自查后收紧：严格合格=passed≥3 且测试文件内至少一处断言或状态比对 → 33 件严格合格（另有 3 件薄证据不计）。
5) 仅自检档单独实跑：公司机 6/13 通过、家机 7/13；其中 1 件经 PR 修复后远端复核通过。
6) 变异检查：A+B 档 30 件各注入 1 处语义变异，22 件 KILLED、8 件 SURVIVED，得分 0.733。
7) 竞品对标自述："只在『外人本地复跑可执行测试』这一格补空白；在 SLSA provenance、TUF、CT 日志、C2PA、RB 字节复现五处落后"。
8) 主动承认的边界：执行者是持证人本人，不是无利益第三方；E1 只有 E1-P（同 operator）；uibc-core 版本 DRIFT（登记 0.2.1 / 仓库 0.5.0 / citation 0.4.2）未消。

请回答五问：
A) 上述 8 条的每一条，证据是否足以支撑其宣称？逐条标 SUPPORTED / UNDER-SUPPORTED / UNSUPPORTED 并说明缺什么。
B) 33 件严格合格、22/30 KILLED 这两个数，按你看到的口径是否站得住？还有没有该继续掉的？
C) 竞品对标是否准确？有没有夸大的地方或漏掉的竞争者？
D) 要证伪这套门禁，最省力的攻击路径是什么？
E) 总判决：PASS / FAIL（门禁只认这两个值），并列出必须满足的条件（不超过 5 条）。
```

### 3. 跑

```bash
curl -s https://<你的服务商端点>/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"<模型名>","messages":[{"role":"system","content":"<上面系统段>"},
       {"role":"user","content":"<上面用户段>"}],"temperature":0.3}' \
  > 外部门禁/external_ai/OUT-20261126-01.raw.json
```

### 4. 落证据条目 `外部门禁/external_ai/OUT-20261126-01.json`

```json
{
  "independent": true,
  "vendor": "<服务商>",
  "model": "<模型名>",
  "same_operator": false,
  "reproducible_cmd": "curl 命令原文（含端点与模型，脱敏 key）",
  "artifacts": ["外部门禁/external_ai/OUT-20261126-01.raw.json"],
  "verdict": "pass",
  "reviewed_at": "2026-11-26T..:..:..+08:00",
  "reviewer": "<姓名或组织>"
}
```

`verdict` 只能填 `pass` 或 `fail`。**若审查结论是 CONDITIONAL PASS 或「有条件通过」，按门禁语义应填 `fail`**——门禁只认二值，条件式通过视同未通过，这是刻意的严格。

### 5. 验收

```bash
python external_gate.py --item OUT-20261126-01
# 期望：PASS（exit 0），无任何 missing / != true 提示
python external_gate.py --all
# E1 项从 REFUSE 变为 PASS 后，整体 PASS 计数才会 > 0
```

## 四、E2 同理，且更硬

`check_e2` 要求 `fresh_clone=true`、`who` 不是本人/本人组织前缀、`collaborator != true`、且有 `os/python/steps/exit_code=0/log_path` 六项。这份 RUNBOOK 在 `RUNBOOK_FOR_THIRD_PARTY.md`，照着跑即可产出。

## 五、本轮的如实留痕

我在 `外部门禁/external_ai_peer/E1-P_deepseek_20261126.json` 记了这次的 E1-P 记录（`same_operator: true`），放的是另一个目录，门禁不会把它当成 E1 通过的依据。它只证明「这条路走过、结论是什么」，不构成准入。
