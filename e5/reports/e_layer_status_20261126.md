# E 层现状：门禁真读数与唯一剩下的缺口

## 一、先看真读数，不看叙述

```
python external_gate.py --all
SUMMARY: 36 条，PASS 0，REFUSE 36
```

36 条条目（QUEUE 与 OUT-20261124-01..17、OUT-20261126-01..08）**全部 REFUSE**，原因一字不差是同一句：

> E1 缺证据（missing file 外部门禁/external_ai/&lt;id&gt;.json）；E2 缺证据（missing file 外部门禁/outsider_run/&lt;id&gt;.json）

也就是说，E 段不是「部分过、部分缺」，是**一条都没过**，且缺口高度集中：E1 与 E2。

## 二、五项的真实状态

| 项 | 判据要点 | 当前 | 说明 |
|---|---|---|---|
| **E1** 外部 AI 审查 | `independent=true`、有 vendor/model、`same_operator≠true`、有可复跑命令、artifacts 存在、verdict=pass | **缺** | 本轮取得的是 E1-P（同 operator），门禁不认；交接包已备，任何人可在 10 分钟内产出合规条目 |
| **E2** 无利益第三方实跑 | `fresh_clone=true`、`who` 非本人、非协作者、六项要素齐全、exit 0、日志非空 | **缺** | RUNBOOK 已备（`RUNBOOK_FOR_THIRD_PARTY.md`），等一个真人 |
| **E3** 链接直达 | `link_probe` 当场 GET，逐条 2xx | 未见条目标注 | 待按条目逐项复验 |
| **E4** 可视化 | ≥3 图、0 可加载外链、断网可读 | 实测通过 | `build_external_board.py` → `svg 3, loadable 0`；E5 看板与附录同样 href=0 |
| **E5** 外人全量实测 | 分母 > 0 且有可复跑读数 | **已做** | 254 件入册、61/61 实跑、33 件严格合格、22/30 KILLED；执行者为本人，故只能作 E5 数据，不能冒充 E2 |

## 三、为什么卡在这里

E1 的六个字段里，`same_operator=false` 这一条本人无法满足——它要求另一个人用自己的凭证调模型。E2 同理，`who` 不能是本人或本人组织前缀。

这不是能力问题，是**结构问题**：自证层（S 段）可以无限逼近，准入层（E 段）必须有一个「不是我」的人参与。把这一层也自己代跑，等于自己给自己发准入证。

## 四、本轮把 E1 做成「照抄即过」

`E1交接包_20261126.md` 里放了：

- 提示词全文（原样复制，含本轮已更新的 33 件 / 22-30 这个最新口径）；
- 一条 curl 命令；
- 一个 JSON 模板（六字段），并写明**「CONDITIONAL PASS 按门禁语义必须填 fail」**；
- 验收命令 `python external_gate.py --item <id>`，期望 PASS。

意思是：只要有人愿意用他自己的 key 跑一遍并把 JSON 放进去，E1 就从 REFUSE 变 PASS，不需要他懂这个项目。

## 五、如实留痕

`外部门禁/external_ai_peer/E1-P_deepseek_20261126.json` 记录了本轮的 E1-P（`same_operator: true`、`independent: false`、`counts_toward_e1: false`）。放在 peer 目录而非 `external_ai/`，门禁不会误判——这也是本轮唯一新增的「人工产物」，其余全是实测读数。

## 六、结论

内容层（E5 三层证据 + E4 可视图）已经做到本人能自证的极限；准入层（E1、E2）卡在「另一个人」。在这两项填上之前，任何「已通过发布前审查」的表述都是不成立的——包括我此前把 E1-P 写成 E1 的说法，已在 E1 交接包第一节纠正。
